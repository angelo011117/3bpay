"""Explicit delivery modes; Graph test never exposes client recipients."""
import urllib.error,urllib.parse
from django.conf import settings
from django.core.mail import send_mail
from .graph import access_token,request
def health():
 mode=settings.EMAIL_DELIVERY_MODE
 if mode=='mailpit':return {'mode':mode,'healthy':True,'detail':'Mailpit'}
 if mode not in {'graph_test','graph_live'}:return {'mode':mode,'healthy':False,'detail':'Unsupported mode'}
 if not settings.MICROSOFT_GRAPH_SENDER or not settings.PUBLIC_BASE_URL.startswith('https://'):return {'mode':mode,'healthy':False,'detail':'Sender and HTTPS public URL required'}
 if mode=='graph_test' and not settings.MICROSOFT_GRAPH_TEST_RECIPIENTS:return {'mode':mode,'healthy':False,'detail':'Test allowlist required'}
 return {'mode':mode,'healthy':True,'detail':'Configured'}
def deliver(email):
 state=health()
 if not state['healthy']:raise ValueError(state['detail'])
 if state['mode']=='mailpit':send_mail(email.subject,email.body,None,[email.recipient]);return 'accepted_mailpit'
 recipients=[email.recipient] if state['mode']=='graph_live' else sorted(settings.MICROSOFT_GRAPH_TEST_RECIPIENTS)
 subject=email.subject if state['mode']=='graph_live' else '[TEST - NOT DELIVERED TO CLIENT] '+email.subject
 body=email.body if state['mode']=='graph_live' else 'TEST DELIVERY. Intended client recipient is retained internally only.\n\n'+email.body
 payload={'message':{'subject':subject,'body':{'contentType':'Text','content':body},'toRecipients':[{'emailAddress':{'address':x}} for x in recipients]},'saveToSentItems':True}
 url='https://graph.microsoft.com/v1.0/users/'+urllib.parse.quote(settings.MICROSOFT_GRAPH_SENDER)+'/sendMail'
 try:request(url,data=payload,token=access_token(),extra_headers={'Content-Type':'application/json'})
 except urllib.error.HTTPError as e:raise RuntimeError('Graph rejected: HTTP '+str(e.code))
 except Exception as e:raise RuntimeError('Graph outcome uncertain: '+type(e).__name__)
 return 'accepted_graph'
