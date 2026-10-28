from django.db import migrations,models
from django.db.models import deletion

class Migration(migrations.Migration):
 dependencies=[('billing','0005_graph_extraction')]
 operations=[
  migrations.AddField(model_name='service',name='vercel_project_name',field=models.CharField(blank=True,max_length=200)),
  migrations.AlterField(model_name='service',name='vercel_project_id',field=models.CharField(blank=True,max_length=200,null=True,unique=True)),
  migrations.AddField(model_name='billingsettings',name='external_actions_enabled',field=models.BooleanField(default=False)),
  migrations.CreateModel(name='OutboxAttempt',fields=[
   ('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),
   ('started_at',models.DateTimeField(auto_now_add=True)),('completed_at',models.DateTimeField(blank=True,null=True)),
   ('outcome',models.CharField(max_length=20)),('detail',models.TextField(blank=True)),('provider_id',models.CharField(blank=True,max_length=255)),
   ('email',models.ForeignKey(on_delete=deletion.CASCADE,related_name='delivery_attempts',to='billing.outboxemail')),
  ]),
 ]
