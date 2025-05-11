"""
ASGI config for gestionM project.

It exposes the ASGI callable as a module-level variable named ``application``.
Combines standard Django ASGI application with Channels routing.
"""

import os
from django.core.asgi import get_asgi_application
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.urls import path

# Configuration du module de paramètres Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestionM.settings')

# Chargement anticipé de l'application Django
django_asgi_app = get_asgi_application()

# Import du consommateur WebSocket après l'initialisation de Django
from api.consumers import StockConsumer

# Définition des routes WebSocket
websocket_urlpatterns = [
    path('ws/stock/', StockConsumer.as_asgi()),
]

# Définition du routeur ASGI combiné
application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})
