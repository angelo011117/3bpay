from django.core.management.base import BaseCommand
from django.conf import settings
import urllib.parse
from billing.graph import configured,access_token,request,is_candidate
from billing.models import GraphMessage
class Command(BaseCommand):
 help='Targeted Graph search for Zelle receipt subjects; does not touch the delta cursor.'
 def handle(self,*args,**kwargs):
  if not configured():raise Exception('Graph is disabled or incomplete')
  mail=urllib.parse.quote(settings.MICROSOFT_GRAPH_MAILBOX)
  query=urllib.parse.urlencode({'$search':'"received a Zelle"','$select':'id,receivedDateTime,from,subject,bodyPreview','$top':'25'})
  url=f'https://graph.microsoft.com/v1.0/users/{mail}/messages?{query}';page=request(url,token=access_token(),extra_headers={'ConsistencyLevel':'eventual'});made=0;requeued=0
  for x in page.get('value',[]):
   defaults={'received_at':x['receivedDateTime'],'sender':x.get('from',{}).get('emailAddress',{}).get('address',''),'subject':x.get('subject',''),'body_excerpt':x.get('bodyPreview','')[:1000]}
   message,created=GraphMessage.objects.get_or_create(graph_id=x['id'],defaults=defaults);made+=int(created)
   # A previous broad delta import may have classified this before its body was
   # fetched. Re-open only an authenticated receipt candidate for parsing.
   if is_candidate(message) and message.status == 'ignored':
    message.status='incident';message.error='Queued for targeted parser retry';message.save(update_fields=['status','error']);requeued+=1
  self.stdout.write(f'imported={made}; requeued={requeued}; matched={len(page.get("value",[]))}')
