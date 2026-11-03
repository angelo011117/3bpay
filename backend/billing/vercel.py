"""Vercel project adapter. Simulation is the safe default.

An absent pause indicator is deliberately *not* treated as active.  Vercel's
project response has changed over time, so a live action is only reconciled
when the API gives an explicit boolean ``paused`` value.  This keeps an
unknown response observable and retryable without guessing about a customer's
site.
"""
import json,urllib.parse,urllib.request
from django.conf import settings
def configured():return settings.VERCEL_ENABLED and settings.VERCEL_MODE=='live' and bool(settings.VERCEL_TOKEN)
def _url(path):return 'https://api.vercel.com'+path+('?teamId='+urllib.parse.quote(settings.VERCEL_TEAM_ID) if settings.VERCEL_TEAM_ID else '')
def _request(path,method='GET'):
 req=urllib.request.Request(_url(path),headers={'Authorization':'Bearer '+settings.VERCEL_TOKEN},method=method)
 with urllib.request.urlopen(req,timeout=20) as response:return json.load(response) if response.headers.get('Content-Type','').startswith('application/json') else {}
def project(project_id):
 if not configured():return {'mode':'simulation','id':project_id,'paused':None}
 return _request('/v9/projects/'+urllib.parse.quote(project_id))
def change(project_id,action):
 if not configured():return {'mode':'simulation','action':action,'id':project_id,'accepted':True}
 return _request('/v1/projects/'+urllib.parse.quote(project_id)+'/'+('pause' if action=='suspend' else 'unpause'),'POST')
class VercelProvider:
 """Production provider used only when Vercel is explicitly enabled/live."""
 is_live=True
 def observe(self,project_id):
  data=project(project_id)
  paused=data.get('paused')
  if paused is True:return 'suspended'
  if paused is False:return 'active'
  return None
 def change(self,project_id,action):
  change(project_id,action)
  # The mutation endpoint acknowledges the request but is not authoritative
  # for state.  Reconciliation obtains observed state on the next pass.
  return None
def provider_for_settings():
 return VercelProvider() if configured() else SimulatedProvider()
class SimulatedProvider:
 is_live=False
 def __init__(self,state='active',outcome='success'):self.state=state;self.outcome=outcome;self.calls=[]
 def observe(self,project_id):return self.state
 def change(self,project_id,action):
  self.calls.append(action)
  if self.outcome=='timeout_before':raise TimeoutError('before_apply')
  self.state='suspended' if action=='suspend' else 'active'
  if self.outcome=='timeout_after':raise TimeoutError('after_apply')
  if self.outcome=='failure':raise RuntimeError('provider_failure')
  return self.state
