from django.db import migrations,models

class Migration(migrations.Migration):
 dependencies=[('billing','0008_provideraction_claim_lease')]
 operations=[migrations.AlterField(model_name='service',name='frequency',field=models.CharField(choices=[('monthly','Monthly'),('semiannual','Semiannual'),('yearly','Annual')],max_length=10))]
