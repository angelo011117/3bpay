import secrets
from decimal import Decimal
from django.db import models
from django.db.models import Sum
from django.utils import timezone

class Client(models.Model):
    business_name=models.CharField(max_length=200); contact_name=models.CharField(max_length=200); email=models.EmailField(); phone=models.CharField(max_length=50,blank=True); active=models.BooleanField(default=True); notes=models.TextField(blank=True)
    def __str__(self): return self.business_name
class PayerAlias(models.Model):
    client=models.ForeignKey(Client,on_delete=models.CASCADE,related_name='aliases'); name=models.CharField(max_length=200)
    class Meta: constraints=[models.UniqueConstraint(fields=['client','name'],name='unique_alias_per_client')]
class Service(models.Model):
    MONTHLY='monthly'; YEARLY='yearly'; ACTIVE='active'; SUSPENDED='suspended'; CANCELLED='cancelled'
    client=models.ForeignKey(Client,on_delete=models.PROTECT,related_name='services'); name=models.CharField(max_length=200); domain=models.CharField(max_length=255); amount=models.DecimalField(max_digits=10,decimal_places=2); frequency=models.CharField(max_length=10,choices=[(MONTHLY,'Monthly'),(YEARLY,'Annual')]); start_date=models.DateField(); next_due_date=models.DateField(); grace_days=models.PositiveSmallIntegerField(default=7); vercel_project_id=models.CharField(max_length=200,blank=True); status=models.CharField(max_length=12,default=ACTIVE); automation_enabled=models.BooleanField(default=False); suspension_exempt_until=models.DateField(null=True,blank=True); exemption_reason=models.TextField(blank=True); desired_state=models.CharField(max_length=12,default=ACTIVE); observed_state=models.CharField(max_length=12,default=ACTIVE)
class Charge(models.Model):
    PENDING='pending'; PARTIAL='partial'; PAID='paid'; VOID='void'
    service=models.ForeignKey(Service,on_delete=models.PROTECT,related_name='charges'); client=models.ForeignKey(Client,on_delete=models.PROTECT); description=models.CharField(max_length=255); period_start=models.DateField(); period_end=models.DateField(); amount=models.DecimalField(max_digits=10,decimal_places=2); due_date=models.DateField(); suspension_at=models.DateTimeField(); public_reference=models.CharField(max_length=24,unique=True); portal_token=models.CharField(max_length=64,unique=True,default=secrets.token_urlsafe); status=models.CharField(max_length=10,default=PENDING); void_reason=models.TextField(blank=True)
    class Meta: constraints=[models.UniqueConstraint(fields=['service','period_start'],name='unique_charge_service_period')]
    @property
    def applied_total(self): return self.allocations.aggregate(v=Sum('amount'))['v'] or Decimal('0')
    @property
    def balance(self): return self.amount-self.applied_total
class Payment(models.Model):
    REVIEW='review'; CONFIRMED='confirmed'; DISCARDED='discarded'
    amount=models.DecimalField(max_digits=10,decimal_places=2); received_at=models.DateTimeField(default=timezone.now); payer_name=models.CharField(max_length=200); recipient_account=models.CharField(max_length=100); transaction_id=models.CharField(max_length=200,blank=True,null=True); source=models.CharField(max_length=20,default='manual'); notes=models.TextField(blank=True); status=models.CharField(max_length=12,default=REVIEW); client=models.ForeignKey(Client,null=True,blank=True,on_delete=models.SET_NULL); created_at=models.DateTimeField(auto_now_add=True)
    class Meta: constraints=[models.UniqueConstraint(fields=['recipient_account','transaction_id'],condition=models.Q(transaction_id__isnull=False)&~models.Q(transaction_id=''),name='unique_bank_transaction')]
    @property
    def applied_total(self): return self.allocations.aggregate(v=Sum('amount'))['v'] or Decimal('0')
    @property
    def unapplied(self): return self.amount-self.applied_total
class PaymentAllocation(models.Model):
    payment=models.ForeignKey(Payment,on_delete=models.CASCADE,related_name='allocations'); charge=models.ForeignKey(Charge,on_delete=models.PROTECT,related_name='allocations'); amount=models.DecimalField(max_digits=10,decimal_places=2)
    class Meta: constraints=[models.UniqueConstraint(fields=['payment','charge'],name='one_allocation_per_charge')]
class OutboxEmail(models.Model):
    PENDING='pending'; SENT='sent'; CANCELLED='cancelled'; FAILED='failed'
    recipient=models.EmailField(); template=models.CharField(max_length=64); subject=models.CharField(max_length=255); body=models.TextField(); charge=models.ForeignKey(Charge,null=True,blank=True,on_delete=models.CASCADE); status=models.CharField(max_length=12,default=PENDING); attempts=models.PositiveIntegerField(default=0); next_attempt=models.DateTimeField(default=timezone.now); error=models.TextField(blank=True); sent_at=models.DateTimeField(null=True,blank=True); dedupe_key=models.CharField(max_length=255,unique=True)
class ProviderAction(models.Model):
    PENDING='pending'; SUCCESS='success'; FAILED='failed'; BLOCKED='blocked'
    service=models.ForeignKey(Service,on_delete=models.CASCADE); action=models.CharField(max_length=16); status=models.CharField(max_length=12,default=PENDING); reason=models.TextField(blank=True); system_suspension=models.BooleanField(default=False); created_at=models.DateTimeField(auto_now_add=True); completed_at=models.DateTimeField(null=True,blank=True)
class AuditLog(models.Model):
    actor=models.CharField(max_length=100,default='system'); action=models.CharField(max_length=100); entity=models.CharField(max_length=100); entity_id=models.CharField(max_length=64); reason=models.TextField(blank=True); created_at=models.DateTimeField(auto_now_add=True)
class SchedulerRun(models.Model): started_at=models.DateTimeField(auto_now_add=True); completed_at=models.DateTimeField(null=True,blank=True); healthy=models.BooleanField(default=True); message=models.TextField(blank=True)
class PublicPaymentClaim(models.Model): charge=models.ForeignKey(Charge,on_delete=models.CASCADE); payer_name=models.CharField(max_length=200); note=models.TextField(blank=True); created_at=models.DateTimeField(auto_now_add=True)
class BillingSettings(models.Model):
    recipient_name=models.CharField(max_length=200,blank=True); zelle_contact=models.CharField(max_length=200,blank=True); qr_image=models.ImageField(upload_to='zelle/',blank=True); updated_at=models.DateTimeField(auto_now=True)
    @classmethod
    def current(cls): return cls.objects.get_or_create(pk=1)[0]
class DevelopmentClock(models.Model):
    now=models.DateTimeField(null=True,blank=True); updated_at=models.DateTimeField(auto_now=True)
    @classmethod
    def current(cls): return cls.objects.get_or_create(pk=1)[0]
