from django.db import migrations,models
class Migration(migrations.Migration):
 dependencies=[('billing','0004_graph_sync')]
 operations=[migrations.AddField(model_name='graphmessage',name='payer_name',field=models.CharField(blank=True,max_length=200)),migrations.AddField(model_name='graphmessage',name='recipient_account',field=models.CharField(blank=True,max_length=100)),migrations.AddField(model_name='graphmessage',name='transaction_id',field=models.CharField(blank=True,max_length=200)),migrations.AddField(model_name='graphmessage',name='amount',field=models.DecimalField(blank=True,decimal_places=2,max_digits=10,null=True))]
