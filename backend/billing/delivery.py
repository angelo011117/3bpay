"""Explicit delivery modes; Graph test never exposes client recipients."""
import re
import urllib.error,urllib.parse
from html import escape
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from .graph import access_token,request

def _html_body(body):
 return body if re.search(r'<[a-z][^>]*>',body or '',re.I) else '<p>'+escape(body or '').replace('\n','<br>')+'</p>'

def _plain_body(body):
 return re.sub(r'<[^>]+>','',body or '')
def health():
 mode=settings.EMAIL_DELIVERY_MODE
 if mode=='disabled':return {'mode':mode,'healthy':True,'enabled':False,'detail':'Outbound delivery disabled; outbox is retained'}
 if mode=='mailpit':return {'mode':mode,'healthy':True,'detail':'Mailpit'}
 if mode not in {'graph_test','graph_live'}:return {'mode':mode,'healthy':False,'detail':'Unsupported mode'}
 if not settings.MICROSOFT_GRAPH_SENDER or not settings.PUBLIC_BASE_URL.startswith('https://'):return {'mode':mode,'healthy':False,'detail':'Sender and HTTPS public URL required'}
 if mode=='graph_test' and not settings.MICROSOFT_GRAPH_TEST_RECIPIENTS:return {'mode':mode,'healthy':False,'detail':'Test allowlist required'}
 return {'mode':mode,'healthy':True,'detail':'Configured'}
def deliver(email):
 state=health()
 if state['mode']=='disabled':raise RuntimeError('Outbound delivery is disabled')
 if not state['healthy']:raise ValueError(state['detail'])
 if state['mode']=='mailpit':
  message=EmailMultiAlternatives(email.subject,_plain_body(email.body),None,[email.recipient])
  message.attach_alternative(_html_body(email.body),'text/html')
  message.send()
  return 'accepted_mailpit'
 recipients=[email.recipient] if state['mode']=='graph_live' else sorted(settings.MICROSOFT_GRAPH_TEST_RECIPIENTS)
 subject=email.subject if state['mode']=='graph_live' else '[TEST - NOT DELIVERED TO CLIENT] '+email.subject
 body=_html_body(email.body) if state['mode']=='graph_live' else '<p><strong>TEST DELIVERY.</strong> Intended client recipient is retained internally only.</p>'+_html_body(email.body)
 payload={'message':{'subject':subject,'body':{'contentType':'HTML','content':body},'toRecipients':[{'emailAddress':{'address':x}} for x in recipients]},'saveToSentItems':True}
 url='https://graph.microsoft.com/v1.0/users/'+urllib.parse.quote(settings.MICROSOFT_GRAPH_SENDER)+'/sendMail'
 try:request(url,data=payload,token=access_token(),extra_headers={'Content-Type':'application/json'})
 except urllib.error.HTTPError as e:raise RuntimeError('Graph rejected: HTTP '+str(e.code))
 except Exception as e:raise RuntimeError('Graph outcome uncertain: '+type(e).__name__)
 return 'accepted_graph'
