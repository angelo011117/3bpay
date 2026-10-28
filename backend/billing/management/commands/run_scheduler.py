from django.core.management.base import BaseCommand
from django.utils import timezone
from billing.models import SchedulerRun, OutboxEmail, OutboxAttempt
from billing.services import generate_charges, schedule_actions, schedule_reminders, reconcile_vercel
from billing.vercel import SimulatedProvider
from billing.delivery import deliver
from billing.graph import sync as graph_sync
class Command(BaseCommand):
 help='Run idempotent billing scheduler (simulation provider only)'
 def handle(self,*args,**opts):
  from django.db import connection
  # PostgreSQL advisory lock prevents overlapping scheduler processes. It has no business effect if unavailable.
  with connection.cursor() as cursor:
   cursor.execute("SELECT pg_try_advisory_lock(3303001)"); locked=cursor.fetchone()[0]
  if not locked:self.stdout.write('Scheduler already running');return
  run=SchedulerRun.objects.create(); graph_result=graph_sync(); reconciled=reconcile_vercel(SimulatedProvider()); made=generate_charges(); reminders=schedule_reminders(); actions=schedule_actions()
  from django.conf import settings
  delivery_note='outbox disabled; pending messages retained'
  if settings.EMAIL_DELIVERY_MODE!='disabled':
   delivery_note='outbox processed'
   for e in OutboxEmail.objects.filter(status='pending',next_attempt__lte=timezone.now()).select_related('charge'):
    if e.charge and e.charge.status=='paid': e.status='cancelled';e.save();continue
    attempt=OutboxAttempt.objects.create(email=e,outcome='started')
    try:
     e.error=deliver(e);e.status='sent';e.sent_at=timezone.now();e.attempts+=1;e.save();attempt.outcome='accepted';attempt.detail=e.error
    except Exception as x:
     e.attempts+=1;e.error=str(x);e.status='uncertain' if 'uncertain' in e.error.lower() else ('failed' if e.attempts>=3 else 'pending');e.next_attempt=timezone.now()+timezone.timedelta(minutes=min(60,2**e.attempts));e.save();attempt.outcome=e.status;attempt.detail=e.error
    attempt.completed_at=timezone.now();attempt.save()
  run.completed_at=timezone.now();run.message=f'graph={graph_result}; reconciled={len(reconciled)}; charges={made}; reminders={reminders}; actions={len(actions)}; {delivery_note}';run.save();self.stdout.write(run.message)
  with connection.cursor() as cursor: cursor.execute("SELECT pg_advisory_unlock(3303001)")
