from django.db import migrations,models
class Migration(migrations.Migration):
 dependencies=[('billing','0007_service_project_name_default')]
 operations=[migrations.AddField(model_name='provideraction',name='claimed_at',field=models.DateTimeField(blank=True,null=True)),migrations.AddField(model_name='provideraction',name='claim_token',field=models.CharField(blank=True,max_length=64))]
