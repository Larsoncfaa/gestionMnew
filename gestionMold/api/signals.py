# gestionAgri/signals.py

import logging
from datetime import timedelta

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from django.core.exceptions import ValidationError

from .models import (
    Produit, Order, LoyaltyProgram, ProductReview,
    Payment, Delivery
)
from .utils import send_alert

logger = logging.getLogger(__name__)


# ─── 1) Alerte de stock faible ─────────────────────────────────────────────────
@receiver(post_save, sender=Produit)
def notify_low_stock(sender, instance, **kwargs):
    """
    Quand un produit est sauvegardé et que son stock < 5,
    envoie un message sur le canal 'stock_alerts'.
    """
    if instance.quantite_en_stock < 5:
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            'stock_alerts',
            {
                'type': 'stock_alert',
                'data': {
                    'produit': instance.nom,
                    'stock': instance.quantite_en_stock
                }
            }
        )


# ─── 2) Création de la livraison à la création de commande ────────────────────────
@receiver(post_save, sender=Order)
def create_delivery_for_new_order(sender, instance, created, **kwargs):
    """
    À la création d'une commande, crée automatiquement
    l’enregistrement Delivery associé, si pas déjà présent.
    """
    if created and not hasattr(instance, 'delivery'):
        Delivery.objects.create(order=instance)


# ─── 3) Attribution de points fidélité à la livraison ─────────────────────────────
@receiver(post_save, sender=Order)
def award_loyalty_points_on_delivery(sender, instance, **kwargs):
    """
    Dès qu’une commande passe en status DELIVERED,
    on ajoute les points au programme fidélité du client.
    """
    if instance.status == 'DELIVERED':
        loyalty, _ = LoyaltyProgram.objects.get_or_create(client=instance.client)
        # évite d’ajouter deux fois pour la même commande
        if not any(txn.get('order') == instance.id for txn in loyalty.transactions):
            points = loyalty.add_points(instance)
            logger.debug(f"Ajout de {points} points fidélité pour la commande #{instance.id}")


# ─── 4) Notification sur nouvel avis produit ─────────────────────────────────────
@receiver(post_save, sender=ProductReview)
def notify_on_product_review(sender, instance, created, **kwargs):
    """
    Lorsqu’un client crée un avis, envoie une alerte
    au propriétaire du produit.
    """
    if created:
        try:
            product_owner = instance.product.user
            send_alert(
                recipient=product_owner,
                message=f"Nouvel avis sur {instance.product.name} : {instance.rating}/5"
            )
        except Exception as e:
            logger.error(f"Échec notification avis produit: {e}")


# ─── 5) Mise à jour du paiement et du statut de commande ─────────────────────────
@receiver(post_save, sender=Payment)
def update_order_payment(sender, instance, **kwargs):
    """
    Quand un paiement devient COMPLETED, on met à jour
    le montant payé et le statut de la commande.
    """
    if instance.status == 'COMPLETED':
        order = instance.order
        # somme déjà payée
        paid_so_far = sum(p.amount for p in order.payments.filter(status='COMPLETED'))
        order.paid_amount = paid_so_far
        order.save()
        order.update_payment_status()


# ─── 6) Gestion des erreurs centrales (exemple) ────────────────────────────────────
# (si vous utilisez CustomExceptionMiddleware, laissez-le gérer les exceptions)
