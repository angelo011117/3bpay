from django.db import migrations

SQL='''
CREATE TABLE billing_client (id bigserial PRIMARY KEY,business_name varchar(200) NOT NULL,contact_name varchar(200) NOT NULL,email varchar(254) NOT NULL,phone varchar(50) NOT NULL,active boolean NOT NULL,notes text NOT NULL);
CREATE TABLE billing_payeralias (id bigserial PRIMARY KEY,client_id bigint NOT NULL REFERENCES billing_client(id) ON DELETE CASCADE,name varchar(200) NOT NULL,CONSTRAINT unique_alias_per_client UNIQUE(client_id,name));
CREATE TABLE billing_service (id bigserial PRIMARY KEY,client_id bigint NOT NULL REFERENCES billing_client(id),name varchar(200) NOT NULL,domain varchar(255) NOT NULL,amount numeric(10,2) NOT NULL,frequency varchar(10) NOT NULL,start_date date NOT NULL,next_due_date date NOT NULL,grace_days smallint NOT NULL,vercel_project_id varchar(200) NOT NULL,status varchar(12) NOT NULL,automation_enabled boolean NOT NULL,suspension_exempt_until date NULL,exemption_reason text NOT NULL,desired_state varchar(12) NOT NULL,observed_state varchar(12) NOT NULL);
CREATE TABLE billing_charge (id bigserial PRIMARY KEY,service_id bigint NOT NULL REFERENCES billing_service(id),client_id bigint NOT NULL REFERENCES billing_client(id),description varchar(255) NOT NULL,period_start date NOT NULL,period_end date NOT NULL,amount numeric(10,2) NOT NULL,due_date date NOT NULL,suspension_at timestamptz NOT NULL,public_reference varchar(24) NOT NULL UNIQUE,portal_token varchar(64) NOT NULL UNIQUE,status varchar(10) NOT NULL,void_reason text NOT NULL,CONSTRAINT unique_charge_service_period UNIQUE(service_id,period_start));
CREATE TABLE billing_payment (id bigserial PRIMARY KEY,amount numeric(10,2) NOT NULL,received_at timestamptz NOT NULL,payer_name varchar(200) NOT NULL,recipient_account varchar(100) NOT NULL,transaction_id varchar(200) NULL,source varchar(20) NOT NULL,notes text NOT NULL,status varchar(12) NOT NULL,client_id bigint NULL REFERENCES billing_client(id) ON DELETE SET NULL,created_at timestamptz NOT NULL);
CREATE UNIQUE INDEX unique_bank_transaction ON billing_payment(recipient_account,transaction_id) WHERE transaction_id IS NOT NULL AND transaction_id <> '';
CREATE TABLE billing_paymentallocation (id bigserial PRIMARY KEY,payment_id bigint NOT NULL REFERENCES billing_payment(id) ON DELETE CASCADE,charge_id bigint NOT NULL REFERENCES billing_charge(id),amount numeric(10,2) NOT NULL,CONSTRAINT one_allocation_per_charge UNIQUE(payment_id,charge_id));
CREATE TABLE billing_outboxemail (id bigserial PRIMARY KEY,recipient varchar(254) NOT NULL,template varchar(64) NOT NULL,subject varchar(255) NOT NULL,body text NOT NULL,charge_id bigint NULL REFERENCES billing_charge(id) ON DELETE CASCADE,status varchar(12) NOT NULL,attempts integer NOT NULL,next_attempt timestamptz NOT NULL,error text NOT NULL,sent_at timestamptz NULL,dedupe_key varchar(255) NOT NULL UNIQUE);
CREATE TABLE billing_provideraction (id bigserial PRIMARY KEY,service_id bigint NOT NULL REFERENCES billing_service(id) ON DELETE CASCADE,action varchar(16) NOT NULL,status varchar(12) NOT NULL,reason text NOT NULL,system_suspension boolean NOT NULL,created_at timestamptz NOT NULL,completed_at timestamptz NULL);
CREATE TABLE billing_auditlog (id bigserial PRIMARY KEY,actor varchar(100) NOT NULL,action varchar(100) NOT NULL,entity varchar(100) NOT NULL,entity_id varchar(64) NOT NULL,reason text NOT NULL,created_at timestamptz NOT NULL);
CREATE TABLE billing_schedulerrun (id bigserial PRIMARY KEY,started_at timestamptz NOT NULL,completed_at timestamptz NULL,healthy boolean NOT NULL,message text NOT NULL);
CREATE TABLE billing_publicpaymentclaim (id bigserial PRIMARY KEY,charge_id bigint NOT NULL REFERENCES billing_charge(id) ON DELETE CASCADE,payer_name varchar(200) NOT NULL,note text NOT NULL,created_at timestamptz NOT NULL);
'''
class Migration(migrations.Migration):
 initial=True
 dependencies=[]
 operations=[migrations.RunSQL(SQL,migrations.RunSQL.noop)]
