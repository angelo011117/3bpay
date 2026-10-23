from django.db import migrations
class Migration(migrations.Migration):
 dependencies=[('billing','0001_initial')]
 operations=[migrations.RunSQL('''
CREATE TABLE billing_billingsettings (id bigserial PRIMARY KEY,recipient_name varchar(200) NOT NULL,zelle_contact varchar(200) NOT NULL,qr_image varchar(100) NOT NULL,updated_at timestamptz NOT NULL);
CREATE TABLE billing_developmentclock (id bigserial PRIMARY KEY,now timestamptz NULL,updated_at timestamptz NOT NULL);
''',migrations.RunSQL.noop)]
