import secrets
import uuid
from html import escape
from calendar import monthrange
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo
from django.db import transaction
from django.db.models import Q
from django.conf import settings
from django.utils import timezone
from .models import *
NY=ZoneInfo('America/New_York')

def reminder_email_body(charge):
    """Safe, client-friendly HTML for a payment reminder.

    The payment portal is the only interactive control in the email: copying is
    deliberately left to the portal, where it can be implemented accessibly.
    """
    billing=BillingSettings.current()
    contact=billing.zelle_contact or 'Contact 3B Smart Solutions'
    base=settings.PUBLIC_BASE_URL.rstrip('/')
    url=f'{base}/portal/{charge.portal_token}'
    return (
        f'<p><strong>Amount:</strong> ${charge.balance:.2f}</p>'
        f'<p><strong>Zelle contact:</strong> {escape(contact)}</p>'
        '<p><a href="'+escape(url, quote=True)+'" '
        'style="display:inline-block;background:#1677c8;color:#ffffff;'
        'padding:10px 16px;border-radius:6px;text-decoration:none;">'
        'View payment details</a></p>'
    )
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
def billing_cycle_months(service):
    return {Service.MONTHLY:1,Service.SEMIANNUAL:6,Service.YEARLY:12}[service.frequency]
def suspension_time(due, grace):
    return timezone.make_aware(datetime.combine(due+timedelta(days=grace+1),time.min),NY)
def charge_status(charge):
    if charge.status==Charge.VOID:return charge.status
    b=charge.balance
    return Charge.PAID if b<=0 else Charge.PARTIAL if b<charge.amount else Charge.PENDING
def generate_charges(now=None):
    # Charges are created seven calendar days before the due date.  That gives
    # the reminder scheduler a real charge to notify about at the promised
    # seven-day point, while preserving the original due date and billing anchor.
    today=(now or business_now()).astimezone(NY).date(); horizon=today+timedelta(days=7); count=0
    for s in Service.objects.exclude(status=Service.CANCELLED):
        due=s.next_due_date
        if due>horizon: continue
        with transaction.atomic():
            months=billing_cycle_months(s)
            c, made=Charge.objects.get_or_create(service=s,period_start=due,defaults={'client':s.client,'description':s.name,'period_end':add_months(due,months)-timedelta(days=1),'amount':s.amount,'due_date':due,'suspension_at':suspension_time(due,s.grace_days),'public_reference':secrets.token_hex(8).upper()})
            if made: count+=1
            # Preserve the original calendar anchor: the next date derives from the prior due date, never payment date.
            s.next_due_date=add_months(due,months); s.save(update_fields=['next_due_date'])
    return count
def issue_recovery_notice(charge,now=None):
    """Start a fresh, auditable seven-full-day grace window for an old charge.

    This is intentionally an explicit administrative action, never a catch-up
    side effect of the scheduler.  The original due date and financial record
    remain unchanged.
    """
    if charge.status not in (Charge.PENDING,Charge.PARTIAL):
        raise ValueError('A recovery notice can only be issued for an unpaid charge')
    local_now=(now or business_now()).astimezone(NY)
    grace_until=local_now.date()+timedelta(days=7)
    service=charge.service
    service.suspension_exempt_until=grace_until
    service.exemption_reason='Recovery grace issued for overdue charge #{0}'.format(charge.id)
    service.save(update_fields=['suspension_exempt_until','exemption_reason'])
    key='{}:recovery_grace:{}'.format(charge.id,local_now.date().isoformat())
    email,created=OutboxEmail.objects.get_or_create(
        dedupe_key=key,
        defaults={
            'recipient':charge.client.email,
            'template':'recovery_grace',
            'subject':'Action required: seven-day payment grace period',
            'body':('<p>Your overdue balance has been given a new seven-day grace period through '
                    '<strong>{}</strong>. Please complete payment before then to avoid service suspension.</p>{}'.format(grace_until,reminder_email_body(charge))),
            'charge':charge,
        },
    )
    return email,created,grace_until
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
def suspension_blockers(charge,now=None):
    now=now or business_now();s=charge.service; blockers=[]
    if charge.suspension_at>now:blockers.append('Seven-day grace period has not ended')
    if not BillingSettings.current().external_actions_enabled:blockers.append('Global external actions are disabled')
    if not s.automation_enabled:blockers.append('Service automation is disabled')
    if s.suspension_exempt_until and s.suspension_exempt_until>=now.astimezone(NY).date():blockers.append('Active extension or exemption')
    if Payment.objects.filter(status=Payment.REVIEW).filter(Q(client=charge.client)|Q(allocations__charge=charge)).exists():blockers.append('Linked payment awaiting review')
    graph=GraphSyncState.current()
    if graph.status not in ('healthy','disabled'):blockers.append('Bank synchronization is not healthy')
    if not OutboxEmail.objects.filter(charge=charge,template='last_notice',status=OutboxEmail.SENT,sent_at__lte=now-timedelta(hours=24)).exists():blockers.append('Final notice was not accepted 24 hours before suspension')
    if not s.vercel_project_id:blockers.append('No Vercel project is linked')
    return blockers
def schedule_actions(now=None, simulation=True):
    now=now or business_now(); result=[]
    for c in Charge.objects.filter(status__in=[Charge.PENDING,Charge.PARTIAL],suspension_at__lte=now).select_related('service','client'):
        s=c.service
        if s.status!=Service.ACTIVE: continue
        blockers=suspension_blockers(c,now)
        if blockers: ProviderAction.objects.update_or_create(service=s,action='suspend',status=ProviderAction.BLOCKED,defaults={'reason':'; '.join(blockers)});continue
        active_action=ProviderAction.objects.filter(service=s,action='suspend',status__in=[ProviderAction.PENDING,'in_progress','uncertain']).first()
        if active_action: continue
        a=ProviderAction.objects.create(service=s,action='suspend',status=ProviderAction.PENDING,system_suspension=True)
        if simulation:
            a.status=ProviderAction.SUCCESS; a.reason='Simulation mode: provider confirmed pause'; a.completed_at=now; a.save()
            s.status=Service.SUSPENDED; s.desired_state=Service.SUSPENDED; s.observed_state=Service.SUSPENDED; s.save()
        else:
            s.desired_state=Service.SUSPENDED; s.save(update_fields=['desired_state'])
        result.append(a)
    for s in Service.objects.filter(status=Service.SUSPENDED):
        if not ProviderAction.objects.filter(service=s,action='suspend',status=ProviderAction.SUCCESS,system_suspension=True).exists(): continue
        if not Charge.objects.filter(service=s,status__in=[Charge.PENDING,Charge.PARTIAL]).exists():
            active_action=ProviderAction.objects.filter(service=s,action='resume',status__in=[ProviderAction.PENDING,'in_progress','uncertain']).first()
            if active_action: continue
            a=ProviderAction.objects.create(service=s,action='resume',status=ProviderAction.PENDING)
            if simulation:
                a.status=ProviderAction.SUCCESS;a.reason='Simulation mode: provider confirmed resume';a.completed_at=now;a.save()
                s.status=Service.ACTIVE;s.desired_state=Service.ACTIVE;s.observed_state=Service.ACTIVE;s.save()
            else:
                s.desired_state=Service.ACTIVE;s.save(update_fields=['desired_state'])
            result.append(a)
    return result
def reconcile_vercel(provider):
    """Recover pending/uncertain actions by observing before any repeat."""
    result=[]
    expiry=timezone.now()-timedelta(minutes=5)
    ProviderAction.objects.filter(status='in_progress',claimed_at__lt=expiry).update(status='uncertain',reason='Expired claim recovered')
    ids=list(ProviderAction.objects.filter(status__in=[ProviderAction.PENDING,'uncertain']).values_list('id',flat=True))
    for action_id in ids:
        # Claim atomically, then release the database transaction before provider I/O.
        token=uuid.uuid4().hex
        claimed=ProviderAction.objects.filter(pk=action_id,status__in=[ProviderAction.PENDING,'uncertain']).update(status='in_progress',reason='Claimed for reconciliation',claimed_at=timezone.now(),claim_token=token)
        if not claimed: continue
        action=ProviderAction.objects.select_related('service').get(pk=action_id)
        service=action.service; observed=provider.observe(service.vercel_project_id)
        if action.action=='suspend' and not Charge.objects.filter(service=service,status__in=[Charge.PENDING,Charge.PARTIAL]).exists():
            action.status=ProviderAction.FAILED;action.reason='Obsolete suspension: payment cleared overdue balance';action.save();service.desired_state=Service.ACTIVE;service.status=Service.ACTIVE;service.observed_state=observed;service.save();result.append(action);continue
        if observed not in (Service.ACTIVE,Service.SUSPENDED):
            ProviderAction.objects.filter(pk=action.pk,claim_token=token,status='in_progress').update(status='uncertain',reason='Provider state is unknown; observation required before retry')
            result.append(action);continue
        service.observed_state=observed;service.save(update_fields=['observed_state'])
        target=Service.SUSPENDED if action.action=='suspend' else Service.ACTIVE
        if observed==target:
            ProviderAction.objects.filter(pk=action.pk,claim_token=token,status='in_progress').update(status=ProviderAction.SUCCESS,completed_at=timezone.now(),reason='Reconciled observed state');service.status=target;service.save(update_fields=['status']);result.append(action);continue
        try:
            provider.change(service.vercel_project_id,action.action)
            # A live provider only acknowledges a mutation.  It is left pending
            # until a subsequent observation confirms the desired state.
            if getattr(provider,'is_live',False):
                ProviderAction.objects.filter(pk=action.pk,claim_token=token,status='in_progress').update(status='uncertain',reason='Provider accepted request; observation required before completion')
            else:
                ProviderAction.objects.filter(pk=action.pk,claim_token=token,status='in_progress').update(status=ProviderAction.SUCCESS,completed_at=timezone.now(),reason='Provider confirmed');service.status=target;service.desired_state=target;service.observed_state=target;service.save()
        except TimeoutError:
            ProviderAction.objects.filter(pk=action.pk,claim_token=token,status='in_progress').update(status='uncertain',reason='Timeout; observation required before retry')
        except Exception as error:
            ProviderAction.objects.filter(pk=action.pk,claim_token=token,status='in_progress').update(status=ProviderAction.FAILED,reason=str(error))
        result.append(action)
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
        _,created=OutboxEmail.objects.get_or_create(dedupe_key=key,defaults={'recipient':c.client.email,'template':template,'subject':'3B Smart Solutions billing reminder','body':reminder_email_body(c),'charge':c})
        made+=int(created)
    return made
