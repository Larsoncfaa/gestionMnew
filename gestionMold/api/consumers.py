import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser

class StockConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user", None)

        # Vérification de l'authentification
        if user is None or isinstance(user, AnonymousUser) or not user.is_authenticated:
            await self.close()
        else:
            self.user = user
            self.group_name = f"user_{user.id}_stock"

            # Joindre le groupe
            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name
            )

            await self.accept()
            await self.send(text_data=json.dumps({
                'message': f'Connexion réussie pour {self.user.email}'
            }))

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            # Quitter le groupe lors de la déconnexion
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        data = json.loads(text_data)

        # Exemple : action = 'update', payload = {...}
        action = data.get('action')
        payload = data.get('payload')

        # Traitement des actions
        if action == 'ping':
            await self.send(text_data=json.dumps({'message': 'pong'}))
        elif action == 'update_stock':
            await self.handle_stock_update(payload)
        else:
            await self.send(text_data=json.dumps({'error': 'Action inconnue'}))

    async def send_stock_update(self, event):
        """Reçoit un événement depuis un autre processus et envoie au client WebSocket"""
        # Diffusion d'une mise à jour du stock à tous les clients connectés
        await self.send(text_data=json.dumps({
            'type': 'stock_update',
            'payload': event['payload']
        }))

    @database_sync_to_async
    def handle_stock_update(self, payload):
        # Logique de mise à jour du stock
        # Exemple : ici tu pourrais enregistrer en base ou effectuer des calculs
        print(f"[DEBUG] Mise à jour du stock reçue : {payload}")

        # Ajouter ici la logique réelle de mise à jour du stock, par exemple:
        # - Validation des données reçues
        # - Mise à jour de l'objet `Product` en base de données
        # Exemple de mise à jour :
        # product = Product.objects.get(id=payload['product_id'])
        # product.quantity_in_stock = payload['new_quantity']
        # product.save()

        # Envoi de la mise à jour à tous les clients
        self.send_stock_update({'payload': payload})

