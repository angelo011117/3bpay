from django.core.management.base import BaseCommand
from django.utils import timezone
from billing.models import SchedulerRun, OutboxEmail
from billing.services import generate_charges, schedule_actions, schedule_reminders
from django.core.mail import send_mail
from billing.graph import sync as graph_sync
class Command(BaseCommand):
 help='Run idempotent billing scheduler (simulation provider only)'
 def handle(self,*args,**opts):
  from django.db import connection
  # PostgreSQL advisory lock prevents overlapping scheduler processes. It has no business effect if unavailable.
  with connection.cursor() as cursor:
   cursor.execute("SELECT pg_try_advisory_lock(3303001)"); locked=cursor.fetchone()[0]
  if not locked:self.stdout.write('Scheduler already running');return
  run=SchedulerRun.objects.create(); graph_result=graph_sync(); made=generate_charges(); reminders=schedule_reminders(); actions=schedule_actions()
  for e in OutboxEmail.objects.filter(status='pending',next_attempt__lte=timezone.now()).select_related('charge'):
   if e.charge and e.charge.status=='paid': e.status='cancelled';e.save();continue
   try: send_mail(e.subject,e.body,None,[e.recipient]);e.status='sent';e.sent_at=timezone.now();e.attempts+=1;e.save()
   except Exception as x: e.attempts+=1;e.error=str(x);e.save()
  run.completed_at=timezone.now();run.message=f'graph={graph_result}; charges={made}; reminders={reminders}; actions={len(actions)}';run.save();self.stdout.write(run.message)
  with connection.cursor() as cursor: cursor.execute("SELECT pg_advisory_unlock(3303001)")
