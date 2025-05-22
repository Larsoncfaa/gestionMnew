# gestionM/urls.py

from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

from api.views import PredictionView

urlpatterns = [
    # Page d'accueil et tableau de bord
    path('', TemplateView.as_view(template_name='accueil.html'), name='home'),
    path('dashboard-ui/', TemplateView.as_view(template_name='dashboard.html'), name='dashboard-ui'),

    # Administration Django
    path('admin/', admin.site.urls),

    # API principale
    path('api/', include('api.urls')),

    # Authentification (Djoser + JWT)
    path('auth/', include('djoser.urls')),
    path('auth/', include('djoser.urls.jwt')),

    # Prédiction IA via formulaire
    path('ia/predict/form/', PredictionView.as_view(), name='predict-form'),

    # Schéma OpenAPI
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    # Swagger UI sans with_ui()
    path(
        'api/docs/swagger/',
        SpectacularSwaggerView.as_view(url_name='schema'),
        name='swagger-ui'
    ),
    # ReDoc UI sans with_ui()
    path(
        'api/docs/redoc/',
        SpectacularRedocView.as_view(url_name='schema'),
        name='redoc'
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
