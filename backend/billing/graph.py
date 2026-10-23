"""App-only Microsoft Graph reader. Never logs credentials or raw message bodies."""
import json, urllib.parse, urllib.request
from django.conf import settings
from django.utils import timezone
from .models import GraphSyncState,GraphMessage
def configured():
 return settings.MICROSOFT_GRAPH_ENABLED and all([settings.MICROSOFT_GRAPH_TENANT_ID,settings.MICROSOFT_GRAPH_CLIENT_ID,settings.MICROSOFT_GRAPH_CLIENT_SECRET,settings.MICROSOFT_GRAPH_MAILBOX])
def request(url,data=None,token=None):
 headers={'Content-Type':'application/x-www-form-urlencoded'} if data else {}
 if token:headers={'Authorization':'Bearer '+token,'Accept':'application/json'}
 req=urllib.request.Request(url,data=urllib.parse.urlencode(data).encode() if data else None,headers=headers,method='POST' if data else 'GET')
 with urllib.request.urlopen(req,timeout=20) as r:return json.load(r)
def access_token():
 return request(f'https://login.microsoftonline.com/{settings.MICROSOFT_GRAPH_TENANT_ID}/oauth2/v2.0/token',{'client_id':settings.MICROSOFT_GRAPH_CLIENT_ID,'client_secret':settings.MICROSOFT_GRAPH_CLIENT_SECRET,'grant_type':'client_credentials','scope':'https://graph.microsoft.com/.default'})['access_token']
def sync():
 state=GraphSyncState.current();state.last_attempt=timezone.now()
 if not settings.MICROSOFT_GRAPH_ENABLED:state.status='disabled';state.error='';state.save();return 'disabled'
 if not configured():state.status='misconfigured';state.error='Missing required Graph configuration';state.save();return 'misconfigured'
 try:
  token=access_token();base=f"https://graph.microsoft.com/v1.0/users/{urllib.parse.quote(settings.MICROSOFT_GRAPH_MAILBOX)}/mailFolders/{urllib.parse.quote(settings.MICROSOFT_GRAPH_MAIL_FOLDER)}/messages/delta?$select=id,receivedDateTime,from,subject,bodyPreview"
  url=state.cursor or base;count=0
  while url:
   page=request(url,token=token)
   for item in page.get('value',[]):
    GraphMessage.objects.get_or_create(graph_id=item['id'],defaults={'received_at':item['receivedDateTime'],'sender':item.get('from',{}).get('emailAddress',{}).get('address',''),'subject':item.get('subject',''),'body_excerpt':item.get('bodyPreview','')[:1000]});count+=1
   url=page.get('@odata.nextLink');state.cursor=page.get('@odata.deltaLink',state.cursor);state.last_message_id=(page.get('value') or [{}])[-1].get('id',state.last_message_id);state.save()
  state.status='healthy';state.error='';state.last_success=timezone.now();state.save();return f'imported={count}'
 except Exception as exc:
  state.status='error';state.error=type(exc).__name__;state.save();return 'error'
