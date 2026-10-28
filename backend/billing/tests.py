from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo
from django.test import TestCase,TransactionTestCase,override_settings
from django.core.management import call_command
import threading
from django.db import close_old_connections
from django.utils import timezone
from .models import *
from .services import suspension_time, apply_payment, suggestions, generate_charges, schedule_actions, cancel_obsolete_reminders, reconcile_vercel, reminder_email_body
from .vercel import SimulatedProvider
from .amex_parser import parse_amex_zelle
class BillingRulesTests(TestCase):
 def setUp(self):
  self.client=Client.objects.create(business_name='A',contact_name='A',email='a@example.test')
  self.service=Service.objects.create(client=self.client,name='Care',domain='a.test',amount=Decimal('100'),frequency='monthly',start_date=date(2024,1,31),next_due_date=date(2024,1,31),automation_enabled=True)
 def charge(self):
  generate_charges(timezone.make_aware(datetime(2024,2,1),ZoneInfo('America/New_York')));return Charge.objects.get(service=self.service)
 def test_short_month_and_idempotency(self):
  c=self.charge();self.service.refresh_from_db();self.assertEqual(c.period_end,date(2024,2,28));self.assertEqual(self.service.next_due_date,date(2024,2,29));generate_charges(timezone.make_aware(datetime(2024,2,1),ZoneInfo('America/New_York')));self.assertEqual(Charge.objects.count(),1)
 def test_grace_is_seven_complete_days_across_dst(self):
  self.assertEqual(suspension_time(date(2024,3,10),7),timezone.make_aware(datetime(2024,3,18),ZoneInfo('America/New_York')))
 def test_partial_payment_cannot_overallocate(self):
  c=self.charge();p=Payment.objects.create(amount=Decimal('60'),payer_name='A',recipient_account='x',status=Payment.CONFIRMED,client=self.client);apply_payment(p,c,'60');c.refresh_from_db();self.assertEqual(c.status,Charge.PARTIAL);self.assertEqual(c.balance,Decimal('40'))
  with self.assertRaises(ValueError):apply_payment(p,c,'1')
 def test_duplicate_transaction(self):
  Payment.objects.create(amount=1,payer_name='A',recipient_account='acct',transaction_id='id')
  with self.assertRaises(Exception):Payment.objects.create(amount=1,payer_name='B',recipient_account='acct',transaction_id='id')
 def test_ambiguous_alias_is_not_suggested(self):
  other=Client.objects.create(business_name='B',contact_name='B',email='b@example.test');PayerAlias.objects.create(client=self.client,name='Same');PayerAlias.objects.create(client=other,name='Same');p=Payment.objects.create(amount=1,payer_name='Same',recipient_account='x');self.assertEqual(suggestions(p)['status'],'ambiguous')
 def test_portal_token_revocation(self):
  c=self.charge();old=c.portal_token;c.portal_token='new-secure-token';c.save();self.assertFalse(Charge.objects.filter(portal_token=old).exists())
 def test_paid_charge_cancels_pending_reminders(self):
  c=self.charge();e=OutboxEmail.objects.create(recipient='a@example.test',template='due_today',subject='x',body='x',charge=c,dedupe_key='notice');cancel_obsolete_reminders(c);e.refresh_from_db();self.assertEqual(e.status,OutboxEmail.CANCELLED)
 @override_settings(PUBLIC_BASE_URL='https://pay.example.test')
 def test_reminder_email_has_labeled_values_and_https_portal_button(self):
  c=self.charge();settings=BillingSettings.current();settings.zelle_contact='zelle@example.test';settings.save()
  body=reminder_email_body(c)
  self.assertIn('<strong>Amount:</strong> $100.00',body)
  self.assertIn('<strong>Zelle contact:</strong> zelle@example.test',body)
  self.assertIn('https://pay.example.test/portal/',body)
  self.assertIn('View payment details',body)
  self.assertNotIn('Copy',body)
 @override_settings(EMAIL_DELIVERY_MODE='disabled',MICROSOFT_GRAPH_ENABLED=False)
 def test_disabled_delivery_keeps_outbox_pending_without_attempt(self):
  c=self.charge();e=OutboxEmail.objects.create(recipient='a@example.test',template='due_today',subject='x',body='x',charge=c,dedupe_key='disabled-delivery')
  call_command('run_scheduler')
  e.refresh_from_db();self.assertEqual(e.status,OutboxEmail.PENDING);self.assertEqual(e.attempts,0);self.assertFalse(e.delivery_attempts.exists())
 def test_pending_linked_payment_blocks_suspension(self):
  c=self.charge();c.suspension_at=timezone.now()-timezone.timedelta(seconds=1);c.save();Payment.objects.create(amount=1,payer_name='A',recipient_account='q',client=self.client);schedule_actions();self.assertTrue(ProviderAction.objects.filter(service=self.service,status=ProviderAction.BLOCKED).exists())
 def test_no_reactivation_of_manual_pause(self):
  self.service.status=Service.SUSPENDED;self.service.save();schedule_actions();self.service.refresh_from_db();self.assertEqual(self.service.status,Service.SUSPENDED)
 def test_real_amex_label_structure(self):
  result=parse_amex_zelle('<p>Zelle payment has been deposited</p><p>Amount:</p><p>$125.50</p><p>From:</p><p>Example Payer</p><p>Account:</p><p>Account ending: 1234</p><p>Transaction ID:</p><p>ABC-123</p><p>To view this payment</p>');self.assertEqual(result['amount'],Decimal('125.50'));self.assertEqual(result['payer_name'],'Example Payer');self.assertEqual(result['recipient_account'],'1234')
 def test_amex_missing_required_field_is_incident(self):
  with self.assertRaises(ValueError):parse_amex_zelle('<p>Zelle payment has been deposited</p><p>Amount: $10</p>')
 def test_vercel_timeout_after_apply_reconciles_without_duplicate(self):
  self.charge();self.service.vercel_project_id='prj_test';self.service.save();a=ProviderAction.objects.create(service=self.service,action='suspend',status=ProviderAction.PENDING,system_suspension=True);p=SimulatedProvider(outcome='timeout_after');reconcile_vercel(p);a.refresh_from_db();self.assertEqual(a.status,'uncertain');p.outcome='success';reconcile_vercel(p);a.refresh_from_db();self.assertEqual(a.status,ProviderAction.SUCCESS);self.assertEqual(p.calls.count('suspend'),1)
 def test_vercel_failure_is_visible_and_recoverable(self):
  self.service.vercel_project_id='prj_test2';self.service.save();a=ProviderAction.objects.create(service=self.service,action='resume',status=ProviderAction.PENDING);p=SimulatedProvider(state='suspended',outcome='failure');reconcile_vercel(p);a.refresh_from_db();self.assertEqual(a.status,ProviderAction.FAILED);a.status=ProviderAction.PENDING;a.save();p.outcome='success';reconcile_vercel(p);a.refresh_from_db();self.assertEqual(a.status,ProviderAction.SUCCESS)
 def test_pending_action_recovers_on_later_reconciler_run(self):
  self.charge();self.service.vercel_project_id='prj_later';self.service.save();a=ProviderAction.objects.create(service=self.service,action='suspend',status=ProviderAction.PENDING,system_suspension=True);p=SimulatedProvider(state='suspended');reconcile_vercel(p);a.refresh_from_db();self.assertEqual(a.status,ProviderAction.SUCCESS);self.assertEqual(p.calls,[])
 def test_payment_clears_pending_pause_without_provider_call(self):
  self.service.vercel_project_id='prj_paid';self.service.save();c=self.charge();c.status=Charge.PAID;c.save();a=ProviderAction.objects.create(service=self.service,action='suspend',status=ProviderAction.PENDING,system_suspension=True);p=SimulatedProvider();reconcile_vercel(p);a.refresh_from_db();self.assertEqual(a.status,ProviderAction.FAILED);self.assertEqual(p.calls,[])
 def test_manual_pause_is_not_resumed(self):
  self.service.status=Service.SUSPENDED;self.service.observed_state=Service.SUSPENDED;self.service.save();self.assertEqual(reconcile_vercel(SimulatedProvider(state='suspended')),[])
class VercelConcurrencyTests(TransactionTestCase):
 def test_two_reconcilers_claim_once(self):
  client=Client.objects.create(business_name='C',contact_name='C',email='c@test');service=Service.objects.create(client=client,name='S',domain='s.test',amount=1,frequency='monthly',start_date=date(2024,1,1),next_due_date=date(2024,1,1),vercel_project_id='prj_concurrent');Charge.objects.create(service=service,client=client,description='S',period_start=date(2024,1,1),period_end=date(2024,1,31),amount=1,due_date=date(2024,1,1),suspension_at=timezone.now(),public_reference='CONCURRENT');action=ProviderAction.objects.create(service=service,action='suspend',status=ProviderAction.PENDING,system_suspension=True);provider=SimulatedProvider();barrier=threading.Barrier(2)
  def run():
   close_old_connections();barrier.wait();reconcile_vercel(provider);close_old_connections()
  one=threading.Thread(target=run);two=threading.Thread(target=run);one.start();two.start();one.join();two.join();action.refresh_from_db();self.assertEqual(provider.calls.count('suspend'),1);self.assertEqual(action.status,ProviderAction.SUCCESS)
 def test_expired_claim_is_recovered_after_interruption(self):
  client=Client.objects.create(business_name='R',contact_name='R',email='r@test');service=Service.objects.create(client=client,name='R',domain='r.test',amount=1,frequency='monthly',start_date=date(2024,1,1),next_due_date=date(2024,1,1),vercel_project_id='prj_recover');Charge.objects.create(service=service,client=client,description='R',period_start=date(2024,1,1),period_end=date(2024,1,31),amount=1,due_date=date(2024,1,1),suspension_at=timezone.now(),public_reference='RECOVER');a=ProviderAction.objects.create(service=service,action='suspend',status='in_progress',claimed_at=timezone.now()-timezone.timedelta(minutes=6),claim_token='dead');p=SimulatedProvider();reconcile_vercel(p);a.refresh_from_db();self.assertEqual(a.status,ProviderAction.SUCCESS);self.assertEqual(p.calls,['suspend'])
