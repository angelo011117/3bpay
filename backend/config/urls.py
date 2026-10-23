from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from billing import views
urlpatterns=[path('admin/',admin.site.urls),path('api/',include('billing.urls')),path('portal/<str:token>/',views.public_portal)]+static(settings.MEDIA_URL,document_root=settings.MEDIA_ROOT)
