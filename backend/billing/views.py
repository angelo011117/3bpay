import secrets
from django.conf import settings
from django.core.mail import send_mail
from django.db import IntegrityError
from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.views.decorators.csrf import ensure_csrf_cookie
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from .models import *
from .services import apply_payment, suggestions, cancel_obsolete_reminders, business_now, schedule_actions
def ser_charge(c): return {'id':c.id,'client':c.client.business_name,'description':c.description,'amount':str(c.amount),'balance':str(c.balance),'due_date':c.due_date,'status':c.status,'portal_token':c.portal_token}
def audit(request,action,obj,reason=''):
 AuditLog.objects.create(actor=request.user.username if request.user.is_authenticated else 'system',action=action,entity=obj.__class__.__name__,entity_id=str(obj.pk),reason=reason)
def csrf_token(request): return request.headers.get('X-CSRFToken','')
@api_view(['GET'])
def dashboard(request):
 from django.db.models import Sum
 pending=Charge.objects.exclude(status__in=[Charge.PAID,Charge.VOID])
 return Response({'confirmed_month':str(Payment.objects.filter(status=Payment.CONFIRMED,received_at__month=timezone.now().month).aggregate(v=Sum('amount'))['v'] or 0),'pending_balance':str(sum((c.balance for c in pending),0)),'overdue_balance':str(sum((c.balance for c in pending.filter(due_date__lt=timezone.localdate())),0)),'in_grace':Service.objects.filter(status=Service.ACTIVE).count(),'suspended':Service.objects.filter(status=Service.SUSPENDED).count(),'payments_review':Payment.objects.filter(status=Payment.REVIEW).count(),'simulation_mode':True})
@api_view(['GET','POST'])
def clients(request):
 if request.method=='GET': return Response([{'id':x.id,'business_name':x.business_name,'contact_name':x.contact_name,'email':x.email,'active':x.active} for x in Client.objects.all()])
 x=Client.objects.create(**request.data); return Response({'id':x.id},201)
@api_view(['GET','PATCH','DELETE'])
def client_detail(request,pk):
 x=get_object_or_404(Client,pk=pk)
 if request.method=='GET': return Response({'id':x.id,'business_name':x.business_name,'contact_name':x.contact_name,'email':x.email,'phone':x.phone,'active':x.active,'notes':x.notes,'aliases':[{'id':a.id,'name':a.name}for a in x.aliases.all()],'services':[{'id':s.id,'name':s.name,'domain':s.domain,'status':s.status}for s in x.services.all()]})
 if request.method=='DELETE':x.delete();return Response(status=204)
 for k,v in request.data.items():setattr(x,k,v)
 x.save();audit(request,'client.updated',x);return Response({'id':x.id})
@api_view(['POST','PATCH','DELETE'])
def aliases(request,client_id,pk=None):
 client=get_object_or_404(Client,pk=client_id)
 if request.method=='POST': a=PayerAlias.objects.create(client=client,name=request.data['name']);audit(request,'alias.created',a);return Response({'id':a.id},201)
 a=get_object_or_404(PayerAlias,pk=pk,client=client)
 if request.method=='DELETE':a.delete();return Response(status=204)
 a.name=request.data['name'];a.save();return Response({'id':a.id})
@api_view(['GET','POST'])
def services(request):
 if request.method=='GET': return Response([{'id':x.id,'name':x.name,'client':x.client.business_name,'domain':x.domain,'amount':str(x.amount),'next_due_date':x.next_due_date,'status':x.status} for x in Service.objects.select_related('client')])
 data=request.data.copy(); x=Service.objects.create(**data); return Response({'id':x.id},201)
@api_view(['GET','PATCH'])
def service_detail(request,pk):
 x=get_object_or_404(Service,pk=pk)
 if request.method=='GET':return Response({'id':x.id,'client_id':x.client_id,'name':x.name,'domain':x.domain,'amount':str(x.amount),'frequency':x.frequency,'start_date':x.start_date,'next_due_date':x.next_due_date,'grace_days':x.grace_days,'status':x.status,'automation_enabled':x.automation_enabled,'suspension_exempt_until':x.suspension_exempt_until,'exemption_reason':x.exemption_reason,'desired_state':x.desired_state,'observed_state':x.observed_state})
 for k,v in request.data.items():setattr(x,k,v)
 x.save();audit(request,'service.updated',x);return Response({'id':x.id})
@api_view(['POST'])
def service_extension(request,pk):
 x=get_object_or_404(Service,pk=pk);x.suspension_exempt_until=request.data.get('until');x.exemption_reason=request.data.get('reason','');x.save();audit(request,'service.extension',x,x.exemption_reason);return Response({'ok':True})
@api_view(['GET'])
def charges(request): return Response([ser_charge(c) for c in Charge.objects.select_related('client').all()])
@api_view(['GET','POST'])
def charge_detail(request,pk):
 c=get_object_or_404(Charge.objects.select_related('service','client'),pk=pk)
 if request.method=='POST':
  c.status=Charge.VOID;c.void_reason=request.data.get('reason','');c.save();audit(request,'charge.voided',c,c.void_reason);return Response({'ok':True})
 return Response({**ser_charge(c),'period_start':c.period_start,'period_end':c.period_end,'suspension_at':c.suspension_at,'public_reference':c.public_reference,'history':[{'action':x.action,'reason':x.reason,'at':x.created_at} for x in AuditLog.objects.filter(entity='Charge',entity_id=str(c.pk))]})
@api_view(['GET','POST'])
def payments(request):
 if request.method=='GET': return Response([{'id':p.id,'amount':str(p.amount),'payer_name':p.payer_name,'status':p.status,'transaction_id':p.transaction_id,'suggestion':suggestions(p)} for p in Payment.objects.all()])
 try: p=Payment.objects.create(**request.data); return Response({'id':p.id,'suggestion':suggestions(p)},201)
 except IntegrityError:return Response({'detail':'Duplicate recipient account and transaction ID'},400)
@api_view(['POST'])
def confirm_payment(request,pk):
 p=get_object_or_404(Payment,pk=pk); p.status=Payment.CONFIRMED;p.save();audit(request,'payment.confirmed',p);return Response({'ok':True})
@api_view(['POST'])
def allocate(request,pk):
 try:
  payment=get_object_or_404(Payment,pk=pk);charge=get_object_or_404(Charge,pk=request.data['charge_id']);apply_payment(payment,charge,request.data['amount']);cancel_obsolete_reminders(charge);audit(request,'payment.allocated',payment);return Response({'ok':True})
 except ValueError as e:return Response({'detail':str(e)},400)
@api_view(['POST'])
def regenerate_portal(request,pk):
 c=get_object_or_404(Charge,pk=pk);c.portal_token=secrets.token_urlsafe(32);c.save(update_fields=['portal_token']);return Response({'token':c.portal_token})
@api_view(['GET'])
@permission_classes([AllowAny])
def public_portal(request,token):
 c=get_object_or_404(Charge,portal_token=token)
 s=BillingSettings.current();return JsonResponse({'brand':'3B Smart Solutions','description':c.description,'domain':c.service.domain,'period':f'{c.period_start} to {c.period_end}','amount':str(c.amount),'balance':str(c.balance),'due_date':c.due_date,'grace_ends':str(c.suspension_at.astimezone().date()),'status':c.status,'zelle_recipient':s.zelle_contact,'recipient_name':s.recipient_name,'qr_url':request.build_absolute_uri(s.qr_image.url) if s.qr_image else None})
@api_view(['POST'])
@permission_classes([AllowAny])
def public_claim(request,token):
 c=get_object_or_404(Charge,portal_token=token)
 if PublicPaymentClaim.objects.filter(charge=c,created_at__gte=timezone.now()-timezone.timedelta(hours=1)).count()>=3:return Response({'detail':'Try again later'},429)
 PublicPaymentClaim.objects.create(charge=c,payer_name=request.data.get('payer_name',''),note=request.data.get('note',''));return Response({'detail':'Thank you. Your payment remains pending verification.'})
@api_view(['GET'])
@permission_classes([AllowAny])
@ensure_csrf_cookie
def csrf(request): return Response({'ok':True})
@api_view(['POST'])
@permission_classes([AllowAny])
def session_login(request):
 user=authenticate(request,username=request.data.get('username',''),password=request.data.get('password',''))
 if not user:return Response({'detail':'Invalid credentials'},400)
 login(request,user);return Response({'ok':True})
@api_view(['GET'])
@permission_classes([AllowAny])
def session_status(request):
 """Small same-origin session probe used by the private Next.js screens."""
 if not request.user.is_authenticated:
  return Response({'authenticated':False},401)
 return Response({'authenticated':True,'username':request.user.get_username()})
@api_view(['POST'])
def session_logout(request): logout(request);return Response({'ok':True})
@api_view(['GET'])
def reminders(request):return Response([{'id':e.id,'recipient':e.recipient,'template':e.template,'status':e.status,'attempts':e.attempts,'charge_id':e.charge_id,'sent_at':e.sent_at,'error':e.error}for e in OutboxEmail.objects.all().order_by('-id')])
@api_view(['GET'])
def actions(request):return Response([{'id':a.id,'service':a.service.name,'action':a.action,'status':a.status,'reason':a.reason,'created_at':a.created_at}for a in ProviderAction.objects.select_related('service').all().order_by('-id')])
@api_view(['GET'])
def audits(request):return Response([{'id':a.id,'actor':a.actor,'action':a.action,'entity':a.entity,'entity_id':a.entity_id,'reason':a.reason,'created_at':a.created_at}for a in AuditLog.objects.all().order_by('-id')])
@api_view(['GET','PUT'])
def billing_settings(request):
 s=BillingSettings.current()
 if request.method=='PUT':
  s.recipient_name=request.data.get('recipient_name','');s.zelle_contact=request.data.get('zelle_contact','');upload=request.FILES.get('qr_image')
  if upload:
   if upload.size>2*1024*1024 or upload.content_type not in ('image/png','image/jpeg','image/webp'):return Response({'detail':'QR must be PNG, JPEG or WebP and at most 2 MB'},400)
   s.qr_image=upload
  s.save();audit(request,'settings.updated',s);return Response({'ok':True})
 return Response({'recipient_name':s.recipient_name,'zelle_contact':s.zelle_contact,'qr_url':s.qr_image.url if s.qr_image else None})
@api_view(['GET','PUT','DELETE'])
def development_clock(request):
 from django.conf import settings
 if not settings.DEBUG:return Response(status=404)
 c=DevelopmentClock.current()
 if request.method=='PUT':c.now=request.data.get('now');c.save();return Response({'now':c.now})
 if request.method=='DELETE':c.now=None;c.save();return Response({'now':None})
 return Response({'now':c.now,'effective_now':business_now()})
@api_view(['POST'])
def simulate_actions(request):
 result=schedule_actions();return Response({'actions':len(result),'simulation_mode':True})
