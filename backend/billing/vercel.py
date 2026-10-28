"""Vercel project adapter. Simulation is the safe default."""
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
class SimulatedProvider:
 def __init__(self,state='active',outcome='success'):self.state=state;self.outcome=outcome;self.calls=[]
 def observe(self,project_id):return self.state
 def change(self,project_id,action):
  self.calls.append(action)
  if self.outcome=='timeout_before':raise TimeoutError('before_apply')
  self.state='suspended' if action=='suspend' else 'active'
  if self.outcome=='timeout_after':raise TimeoutError('after_apply')
  if self.outcome=='failure':raise RuntimeError('provider_failure')
  return self.state
