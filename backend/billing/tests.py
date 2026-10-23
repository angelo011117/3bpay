from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo
from django.test import TestCase
from django.utils import timezone
from .models import *
from .services import suspension_time, apply_payment, suggestions, generate_charges, schedule_actions, cancel_obsolete_reminders
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
 def test_pending_linked_payment_blocks_suspension(self):
  c=self.charge();c.suspension_at=timezone.now()-timezone.timedelta(seconds=1);c.save();Payment.objects.create(amount=1,payer_name='A',recipient_account='q',client=self.client);schedule_actions();self.assertTrue(ProviderAction.objects.filter(service=self.service,status=ProviderAction.BLOCKED).exists())
 def test_no_reactivation_of_manual_pause(self):
  self.service.status=Service.SUSPENDED;self.service.save();schedule_actions();self.service.refresh_from_db();self.assertEqual(self.service.status,Service.SUSPENDED)
 def test_real_amex_label_structure(self):
  result=parse_amex_zelle('<p>Zelle payment has been deposited</p><p>Amount:</p><p>$125.50</p><p>From:</p><p>Example Payer</p><p>Account:</p><p>Account ending: 1234</p><p>Transaction ID:</p><p>ABC-123</p><p>To view this payment</p>');self.assertEqual(result['amount'],Decimal('125.50'));self.assertEqual(result['payer_name'],'Example Payer');self.assertEqual(result['recipient_account'],'1234')
 def test_amex_missing_required_field_is_incident(self):
  with self.assertRaises(ValueError):parse_amex_zelle('<p>Zelle payment has been deposited</p><p>Amount: $10</p>')
