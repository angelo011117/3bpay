"""App-only Microsoft Graph reader. Never logs credentials or raw message bodies."""
import json, urllib.parse, urllib.request, urllib.error
from datetime import timedelta
from django.conf import settings
from django.utils import timezone
from .models import GraphSyncState,GraphMessage,Payment
from .amex_parser import parse_amex_zelle
PARSER_VERSION='amex-html-v1'
def is_candidate(message):
 sender=(message.sender or '').lower(); subject=(message.subject or '').lower(); preview=(message.body_excerpt or '').lower()
 return sender.endswith('americanexpress.com') and 'zelle' in (subject+' '+preview) and any(x in (subject+' '+preview) for x in ('deposit','deposited','received'))
def fetch_message(token,graph_id):
 base=f"https://graph.microsoft.com/v1.0/users/{urllib.parse.quote(settings.MICROSOFT_GRAPH_MAILBOX)}/messages/{urllib.parse.quote(graph_id)}?$select=id,body,from,subject,receivedDateTime,internetMessageHeaders"
 return request(base,token=token)
def classify_existing():
 """Classify unrelated mail as ignored; fetch candidate bodies only, then parse idempotently."""
 if not configured():return {'ignored':0,'incidents':0,'processed':0}
 token=access_token();out={'ignored':0,'incidents':0,'processed':0}
 for msg in GraphMessage.objects.filter(status__in=['incident','review']):
  if not is_candidate(msg):msg.status='ignored';msg.error='Not an AmEx Zelle deposit notification';msg.save(update_fields=['status','error']);out['ignored']+=1;continue
  try:
   item=fetch_message(token,msg.graph_id);body=item.get('body',{});data=parse_amex_zelle(body.get('content',''))
   msg.payer_name=data['payer_name'];msg.recipient_account=data['recipient_account'];msg.transaction_id=data['transaction_id'];msg.amount=data['amount'];msg.body_excerpt=data['evidence'];msg.status='review';msg.error=f'Parsed by {PARSER_VERSION}';msg.save()
   payment,created=Payment.objects.get_or_create(recipient_account=data['recipient_account'],transaction_id=data['transaction_id'],defaults={'amount':data['amount'],'payer_name':data['payer_name'],'source':'graph','notes':f'Graph message {msg.graph_id}','status':Payment.REVIEW})
   msg.payment=payment;msg.save(update_fields=['payment']);out['processed']+=1
  except Exception as error:
   msg.status='incident';msg.error=f'{PARSER_VERSION}: {type(error).__name__}';msg.save(update_fields=['status','error']);out['incidents']+=1
 return out
def configured():
 return settings.MICROSOFT_GRAPH_ENABLED and all([settings.MICROSOFT_GRAPH_TENANT_ID,settings.MICROSOFT_GRAPH_CLIENT_ID,settings.MICROSOFT_GRAPH_CLIENT_SECRET,settings.MICROSOFT_GRAPH_MAILBOX])
def request(url,data=None,token=None,extra_headers=None):
 headers={'Content-Type':'application/x-www-form-urlencoded'} if data else {}
 if token:headers={'Authorization':'Bearer '+token,'Accept':'application/json'}
 if extra_headers:headers.update(extra_headers)
 payload=json.dumps(data).encode() if isinstance(data,(dict,list)) and extra_headers and extra_headers.get('Content-Type')=='application/json' else urllib.parse.urlencode(data).encode() if data else None
 req=urllib.request.Request(url,data=payload,headers=headers,method='POST' if data else 'GET')
 with urllib.request.urlopen(req,timeout=20) as r:
  return json.load(r) if r.headers.get('Content-Type','').startswith('application/json') else {}
def access_token():
 return request(f'https://login.microsoftonline.com/{settings.MICROSOFT_GRAPH_TENANT_ID}/oauth2/v2.0/token',{'client_id':settings.MICROSOFT_GRAPH_CLIENT_ID,'client_secret':settings.MICROSOFT_GRAPH_CLIENT_SECRET,'grant_type':'client_credentials','scope':'https://graph.microsoft.com/.default'})['access_token']
def sync():
 state=GraphSyncState.current();state.last_attempt=timezone.now()
 if not settings.MICROSOFT_GRAPH_ENABLED:state.status='disabled';state.error='';state.save();return 'disabled'
 if not configured():state.status='misconfigured';state.error='Missing required Graph configuration';state.save();return 'misconfigured'
 try:
  token=access_token();since=(timezone.now()-timedelta(days=settings.MICROSOFT_GRAPH_INITIAL_LOOKBACK_DAYS)).isoformat();base=f"https://graph.microsoft.com/v1.0/users/{urllib.parse.quote(settings.MICROSOFT_GRAPH_MAILBOX)}/mailFolders/{urllib.parse.quote(settings.MICROSOFT_GRAPH_MAIL_FOLDER)}/messages/delta?$select=id,receivedDateTime,from,subject,bodyPreview,body&$filter=receivedDateTime ge {since}"
  url=state.cursor or base;count=0
  while url:
   page=request(url,token=token)
   for item in page.get('value',[]):
    # Delta feeds may include tombstones for moves/deletions. They are not messages to parse.
    if item.get('@removed') or not item.get('id'): continue
    msg,created=GraphMessage.objects.get_or_create(graph_id=item['id'],defaults={'received_at':item['receivedDateTime'],'sender':item.get('from',{}).get('emailAddress',{}).get('address',''),'subject':item.get('subject',''),'body_excerpt':item.get('bodyPreview','')[:1000]})
    if created:
     try:
      data=parse_amex_zelle(item.get('body',{}).get('content',''));msg.payer_name=data['payer_name'];msg.recipient_account=data['recipient_account'];msg.transaction_id=data['transaction_id'];msg.amount=data['amount'];msg.body_excerpt=data['evidence'];msg.save()
      payment=Payment.objects.create(amount=data['amount'],payer_name=data['payer_name'],recipient_account=data['recipient_account'],transaction_id=data['transaction_id'],source='graph',notes=f'Graph message {item["id"]}',status=Payment.REVIEW);msg.payment=payment;msg.save(update_fields=['payment'])
     except Exception as error:msg.status='incident';msg.error=type(error).__name__;msg.save(update_fields=['status','error'])
    count+=int(created)
   url=page.get('@odata.nextLink');state.cursor=page.get('@odata.deltaLink',state.cursor);state.last_message_id=(page.get('value') or [{}])[-1].get('id',state.last_message_id);state.save()
  state.status='healthy';state.error='';state.last_success=timezone.now();state.save();return f'imported={count}'
 except urllib.error.HTTPError as exc:
  # Delta cursors can expire. Reset only the cursor; the bounded initial filter and graph_id uniqueness keep re-entry safe.
  if exc.code==410: state.cursor='';state.status='cursor_expired';state.error='Graph delta cursor expired; retry scheduled';state.save();return 'cursor_expired'
  state.status='error';state.error=f'HTTP {exc.code}';state.save();return 'error'
 except Exception as exc:
  state.status='error';state.error=type(exc).__name__;state.save();return 'error'
