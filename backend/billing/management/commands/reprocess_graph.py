from django.core.management.base import BaseCommand
from billing.graph import classify_existing
class Command(BaseCommand):
 help='Safely classify/reprocess Graph messages; does not confirm or allocate payments.'
 def handle(self,*args,**kwargs):self.stdout.write(str(classify_existing()))
