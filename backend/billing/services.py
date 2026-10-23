import secrets
from calendar import monthrange
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from .models import *
NY=ZoneInfo('America/New_York')
def business_now():
    """Only development/tests may override time; production always uses the real UTC clock."""
    from django.conf import settings
    if settings.DEBUG:
        value=DevelopmentClock.current().now
        if value:return value
    return timezone.now()
def add_months(anchor, months):
    m=anchor.month-1+months; y=anchor.year+m//12; m=m%12+1
    return date(y,m,min(anchor.day,monthrange(y,m)[1]))
def suspension_time(due, grace):
    return timezone.make_aware(datetime.combine(due+timedelta(days=grace+1),time.min),NY)
def charge_status(charge):
    if charge.status==Charge.VOID:return charge.status
    b=charge.balance
    return Charge.PAID if b<=0 else Charge.PARTIAL if b<charge.amount else Charge.PENDING
def generate_charges(now=None):
    today=(now or business_now()).astimezone(NY).date(); count=0
    for s in Service.objects.exclude(status=Service.CANCELLED):
        due=s.next_due_date
        if due>today: continue
        with transaction.atomic():
            c, made=Charge.objects.get_or_create(service=s,period_start=due,defaults={'client':s.client,'description':s.name,'period_end':add_months(due,1 if s.frequency==s.MONTHLY else 12)-timedelta(days=1),'amount':s.amount,'due_date':due,'suspension_at':suspension_time(due,s.grace_days),'public_reference':secrets.token_hex(8).upper()})
            if made: count+=1
            # Preserve the original calendar anchor: the next date derives from the prior due date, never payment date.
            s.next_due_date=add_months(due,1 if s.frequency==s.MONTHLY else 12); s.save(update_fields=['next_due_date'])
    return count
def apply_payment(payment, charge, amount):
    amount=Decimal(str(amount))
    with transaction.atomic():
        payment=Payment.objects.select_for_update().get(pk=payment.pk); charge=Charge.objects.select_for_update().get(pk=charge.pk)
        if payment.status!=Payment.CONFIRMED: raise ValueError('Payment must be confirmed')
        if payment.client_id and payment.client_id!=charge.client_id: raise ValueError('Payment and charge must belong to same client')
        if amount<=0 or amount>payment.unapplied or amount>charge.balance: raise ValueError('Allocation exceeds available amount or charge balance')
        PaymentAllocation.objects.create(payment=payment,charge=charge,amount=amount); charge.status=charge_status(charge); charge.save(update_fields=['status'])
def suggestions(payment):
    name=payment.payer_name.strip().lower(); aliases=PayerAlias.objects.filter(name__iexact=payment.payer_name).select_related('client')
    clients={x.client for x in aliases}
    if not clients:return {'status':'no_match','clients':[]}
    matching=[c for c in clients if Charge.objects.filter(client=c,status__in=[Charge.PENDING,Charge.PARTIAL],amount=payment.amount).exists()]
    if len(clients)!=1 or len(matching)>1:return {'status':'ambiguous','clients':[c.business_name for c in clients]}
    return {'status':'suggested','client':next(iter(clients)).business_name}
def schedule_actions(now=None):
    now=now or business_now(); result=[]
    for c in Charge.objects.filter(status__in=[Charge.PENDING,Charge.PARTIAL],suspension_at__lte=now).select_related('service','client'):
        s=c.service
        if not s.automation_enabled or s.status!=Service.ACTIVE: continue
        if s.suspension_exempt_until and s.suspension_exempt_until>=now.astimezone(NY).date(): continue
        pending=Payment.objects.filter(status=Payment.REVIEW).filter(Q(client=c.client)|Q(allocations__charge=c)).exists()
        if pending: ProviderAction.objects.get_or_create(service=s,action='suspend',status=ProviderAction.BLOCKED,defaults={'reason':'Linked payment awaiting review'}); continue
        a,_=ProviderAction.objects.get_or_create(service=s,action='suspend',status=ProviderAction.PENDING)
        a.status=ProviderAction.SUCCESS; a.reason='Simulation mode: provider confirmed pause'; a.system_suspension=True; a.completed_at=now; a.save(); s.status=Service.SUSPENDED; s.desired_state=Service.SUSPENDED; s.observed_state=Service.SUSPENDED; s.save(); result.append(a)
    for s in Service.objects.filter(status=Service.SUSPENDED):
        if not ProviderAction.objects.filter(service=s,action='suspend',status=ProviderAction.SUCCESS,system_suspension=True).exists(): continue
        if not Charge.objects.filter(service=s,status__in=[Charge.PENDING,Charge.PARTIAL]).exists():
            a=ProviderAction.objects.create(service=s,action='resume',status=ProviderAction.SUCCESS,reason='Simulation mode: provider confirmed resume',completed_at=now); s.status=Service.ACTIVE;s.desired_state=Service.ACTIVE;s.observed_state=Service.ACTIVE;s.save();result.append(a)
    return result
def cancel_obsolete_reminders(charge):
    OutboxEmail.objects.filter(charge=charge,status=OutboxEmail.PENDING).update(status=OutboxEmail.CANCELLED)
def schedule_reminders(now=None):
    """Create exactly one applicable logical notice per charge/run state; dedupe key prevents repeats."""
    today=(now or business_now()).astimezone(NY).date(); made=0
    rules={-7:'seven_days_before',0:'due_today',3:'three_days_overdue'}
    for c in Charge.objects.filter(status__in=[Charge.PENDING,Charge.PARTIAL]).select_related('client'):
        days=(today-c.due_date).days
        template=rules.get(days)
        if today==c.suspension_at.astimezone(NY).date()-timedelta(days=1):template='last_notice'
        if not template:continue
        key=f'{c.id}:{template}'
        _,created=OutboxEmail.objects.get_or_create(dedupe_key=key,defaults={'recipient':c.client.email,'template':template,'subject':'3B Smart Solutions billing reminder','body':f'View and pay your charge at /portal/{c.portal_token}','charge':c})
        made+=int(created)
    return made
