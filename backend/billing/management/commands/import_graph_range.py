from datetime import datetime,time
from django.core.management.base import BaseCommand
from django.utils import timezone
from billing.graph import configured,access_token,request,is_candidate
from billing.models import GraphMessage
import urllib.parse
from django.conf import settings
class Command(BaseCommand):
 help='One-off bounded Graph historical import; never changes the delta cursor.'
 def add_arguments(self,p):p.add_argument('--from-date',required=True);p.add_argument('--to-date',required=True)
 def handle(self,*args,**o):
  if not configured():raise Exception('Graph is disabled or incomplete')
  start=o['from_date']+'T00:00:00Z';end=o['to_date']+'T23:59:59Z';mail=urllib.parse.quote(settings.MICROSOFT_GRAPH_MAILBOX);folder=urllib.parse.quote(settings.MICROSOFT_GRAPH_MAIL_FOLDER)
  query=urllib.parse.urlencode({'$select':'id,receivedDateTime,from,subject,bodyPreview','$filter':f'receivedDateTime ge {start} and receivedDateTime le {end}'})
  url=f"https://graph.microsoft.com/v1.0/users/{mail}/mailFolders/{folder}/messages?{query}"
  token=access_token();made=0
  while url:
   page=request(url,token=token)
   for x in page.get('value',[]):
    _,created=GraphMessage.objects.get_or_create(graph_id=x['id'],defaults={'received_at':x['receivedDateTime'],'sender':x.get('from',{}).get('emailAddress',{}).get('address',''),'subject':x.get('subject',''),'body_excerpt':x.get('bodyPreview','')[:1000]});made+=int(created)
   url=page.get('@odata.nextLink')
  self.stdout.write(f'imported={made}')
