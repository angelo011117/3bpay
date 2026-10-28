from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from billing.models import *
from billing.services import generate_charges
class Command(BaseCommand):
 help='Idempotently load development demonstration data.'
 def handle(self,*args,**kwargs):
  from django.conf import settings
  if not settings.DEBUG: raise Exception('Demo loading is development-only')
  client,_=Client.objects.get_or_create(business_name='Acme Demo LLC',defaults={'contact_name':'Avery Client','email':'avery@example.test'})
  PayerAlias.objects.get_or_create(client=client,name='Avery Client')
  today=timezone.localdate(); service,_=Service.objects.get_or_create(client=client,name='Website Care',defaults={'domain':'acme.example','amount':'125.00','frequency':'monthly','start_date':today-timedelta(days=35),'next_due_date':today})
  generate_charges(); charge=Charge.objects.filter(service=service).order_by('-id').first()
  if charge:
   from billing.services import reminder_email_body
   OutboxEmail.objects.get_or_create(dedupe_key=f'demo-due-{charge.id}',defaults={'recipient':client.email,'template':'due','subject':'Your 3B Smart Solutions payment is due','body':reminder_email_body(charge),'charge':charge})
  Payment.objects.get_or_create(recipient_account='AmEx ••••1234',transaction_id='DEMO-ZELLE-001',defaults={'amount':'125.00','payer_name':'Avery Client','source':'bank_notification','notes':'Example notification: Amount, From, Account, Transaction ID'})
  self.stdout.write('Demo loaded. Run scheduler to send the Mailpit email.')
