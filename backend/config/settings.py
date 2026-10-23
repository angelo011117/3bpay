import os
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'unsafe-development-key')
DEBUG = os.getenv('DJANGO_DEBUG', '0') == '1'
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
INSTALLED_APPS = ['django.contrib.admin','django.contrib.auth','django.contrib.contenttypes','django.contrib.sessions','django.contrib.messages','django.contrib.staticfiles','rest_framework','billing']
MIDDLEWARE = ['django.middleware.security.SecurityMiddleware','django.contrib.sessions.middleware.SessionMiddleware','django.middleware.common.CommonMiddleware','django.middleware.csrf.CsrfViewMiddleware','django.contrib.auth.middleware.AuthenticationMiddleware','django.contrib.messages.middleware.MessageMiddleware','django.middleware.clickjacking.XFrameOptionsMiddleware']
ROOT_URLCONF='config.urls'
TEMPLATES=[{'BACKEND':'django.template.backends.django.DjangoTemplates','DIRS':[],'APP_DIRS':True,'OPTIONS':{'context_processors':['django.template.context_processors.request','django.contrib.auth.context_processors.auth','django.contrib.messages.context_processors.messages']}}]
WSGI_APPLICATION='config.wsgi.application'
DATABASES={'default':{'ENGINE':'django.db.backends.postgresql','NAME':os.getenv('POSTGRES_DB','threebpay'),'USER':os.getenv('POSTGRES_USER','threebpay'),'PASSWORD':os.getenv('POSTGRES_PASSWORD','threebpay'),'HOST':os.getenv('POSTGRES_HOST','db'),'PORT':os.getenv('POSTGRES_PORT','5432')}}
AUTH_PASSWORD_VALIDATORS=[]
LANGUAGE_CODE='en-us'; TIME_ZONE='America/New_York'; USE_I18N=True; USE_TZ=True
STATIC_URL='/static/'; MEDIA_URL='/media/'; MEDIA_ROOT=BASE_DIR/'media'; DEFAULT_AUTO_FIELD='django.db.models.BigAutoField'
EMAIL_HOST=os.getenv('EMAIL_HOST','mailpit'); EMAIL_PORT=int(os.getenv('EMAIL_PORT','1025')); EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend'; DEFAULT_FROM_EMAIL='billing@3bsmartsolutions.example'
REST_FRAMEWORK={'DEFAULT_PERMISSION_CLASSES':['rest_framework.permissions.IsAuthenticated'],'DEFAULT_AUTHENTICATION_CLASSES':['rest_framework.authentication.SessionAuthentication']}
CSRF_TRUSTED_ORIGINS=['http://localhost']
MICROSOFT_GRAPH_ENABLED=os.getenv('MICROSOFT_GRAPH_ENABLED','false').lower()=='true'
MICROSOFT_GRAPH_TENANT_ID=os.getenv('MICROSOFT_GRAPH_TENANT_ID','')
MICROSOFT_GRAPH_CLIENT_ID=os.getenv('MICROSOFT_GRAPH_CLIENT_ID','')
MICROSOFT_GRAPH_CLIENT_SECRET=os.getenv('MICROSOFT_GRAPH_CLIENT_SECRET','')
MICROSOFT_GRAPH_MAILBOX=os.getenv('MICROSOFT_GRAPH_MAILBOX','')
MICROSOFT_GRAPH_MAIL_FOLDER=os.getenv('MICROSOFT_GRAPH_MAIL_FOLDER','inbox')
MICROSOFT_GRAPH_POLL_INTERVAL_SECONDS=int(os.getenv('MICROSOFT_GRAPH_POLL_INTERVAL_SECONDS','300'))
