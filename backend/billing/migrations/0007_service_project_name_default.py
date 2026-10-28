from django.db import migrations,models
class Migration(migrations.Migration):
 dependencies=[('billing','0006_sprint3_delivery_vercel')]
 operations=[migrations.AlterField(model_name='service',name='vercel_project_name',field=models.CharField(blank=True,default='',max_length=200))]
