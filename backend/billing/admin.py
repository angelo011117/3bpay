from django.contrib import admin
from .models import *
admin.site.register([Client,PayerAlias,Service,Charge,Payment,PaymentAllocation,OutboxEmail,ProviderAction,AuditLog,SchedulerRun,PublicPaymentClaim,BillingSettings,DevelopmentClock])
