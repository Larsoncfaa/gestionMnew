import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone
from asgiref.sync import async_to_sync


from .models import Product

class StockConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user", None)

        # Vérification de l'authentification
        if not user or isinstance(user, AnonymousUser) or not user.is_authenticated:
            await self.close()
            return

        self.user = user
        self.group_name = 'stock_alerts'  # correspond au group_send des signaux

        # Joindre le groupe 'stock_alerts'
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()
        await self.send(text_data=json.dumps({
            'message': f'Connexion WebSocket établie pour {self.user.email}'
        }))

    async def disconnect(self, close_code):
        # Quitter le groupe
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get('action')
        payload = data.get('payload')

        if action == 'ping':
            await self.send(text_data=json.dumps({'message': 'pong'}))
        elif action == 'update_stock':
            # On laisse le python sync se charger de la DB, puis on renvoie en WebSocket
            await self.handle_stock_update(payload)
        else:
            await self.send(text_data=json.dumps({'error': 'Action inconnue'}))

    async def stock_alert(self, event):
        """
        Handler pour les événements envoyés par send_group
        (type='stock_alert' dans signals.py).
        """
        await self.send(text_data=json.dumps({
            'type': 'stock_alert',
            'payload': event['data']
        }))

    @database_sync_to_async
    def handle_stock_update(self, payload):
        """
        Exemple de mise à jour de la DB et rebroadcast.
        """
        product_id = payload.get('product_id')
        new_q = payload.get('new_quantity')
        try:
            prod = Product.objects.get(pk=product_id)
            prod.quantity_in_stock = new_q
            prod.save(update_fields=['quantity_in_stock'])

            # Une fois mis à jour, on broadcaste manuellement
            # (directement via channel_layer, synchrone ici)
            async_to_sync(self.channel_layer.group_send)(
                'stock_alerts',
                {
                    'type': 'stock_alert',
                    'data': {
                        'product': prod.name,
                        'stock': prod.quantity_in_stock,
                        'updated_at': timezone.now().isoformat()
                    }
                }
            )
        except Product.DoesNotExist:
            logger = __import__('logging').getLogger(__name__)
            logger.warning(f"Produit #{product_id} introuvable pour update_stock")
