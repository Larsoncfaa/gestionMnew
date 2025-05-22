# api/middleware.py

import logging
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied, ValidationError as DjangoValidationError
from rest_framework.exceptions import APIException, ValidationError as DRFValidationError

from .models import (
    Product, Order, Supplier,
    Warehouse, Batch, StockLevel, StockMovement,
    Invoice, ReturnRequest, ExchangeRequest,
    Notification, PromoCode, ProductDiscount,
    PaymentLog, Payment, Delivery, TrackingInfo,
    Proof, StockAlert, ProductReview, ClientProfile, LoyaltyProgram
)

logger = logging.getLogger(__name__)

class CustomExceptionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        # Log complet de l'exception
        logger.error(f"Exception at {request.path}: {exception}", exc_info=True)

        # Mapping des modèles -> message / code pour DoesNotExist
        not_found_map = {
            Product:        ('Produit non trouvé', 'product_not_found'),
            Order:          ('Commande non trouvée', 'order_not_found'),
            Supplier:       ('Fournisseur non trouvé', 'supplier_not_found'),
            Warehouse:      ('Entrepôt non trouvé', 'warehouse_not_found'),
            Batch:          ('Lot non trouvé', 'batch_not_found'),
            StockLevel:     ('Stock non trouvé', 'stocklevel_not_found'),
            StockMovement:  ('Mouvement de stock non trouvé', 'stockmovement_not_found'),
            Invoice:        ('Facture non trouvée', 'invoice_not_found'),
            ReturnRequest:  ('Demande de retour non trouvée', 'returnrequest_not_found'),
            ExchangeRequest:('Échange non trouvé', 'exchangerequest_not_found'),
            Notification:   ('Notification non trouvée', 'notification_not_found'),
            PromoCode:      ('Code promo non trouvé', 'promocode_not_found'),
            ProductDiscount:('Remise produit non trouvée', 'productdiscount_not_found'),
            PaymentLog:     ('Log de paiement non trouvé', 'paymentlog_not_found'),
            Payment:        ('Paiement non trouvé', 'payment_not_found'),
            Delivery:       ('Livraison non trouvée', 'delivery_not_found'),
            TrackingInfo:   ('Tracking info non trouvée', 'trackinginfo_not_found'),
            Proof:          ('Preuve non trouvée', 'proof_not_found'),
            StockAlert:     ('Alerte de stock non trouvée', 'stockalert_not_found'),
            ProductReview:  ('Avis produit non trouvé', 'productreview_not_found'),
            ClientProfile:  ('Profil client non trouvé', 'clientprofile_not_found'),
            LoyaltyProgram: ('Programme fidélité non trouvé', 'loyaltyprogram_not_found'),
        }

        # Vérifier les DoesNotExist
        for model_cls, (msg, code) in not_found_map.items():
            if isinstance(exception, model_cls.DoesNotExist):
                return JsonResponse({'error': msg, 'code': code}, status=404)

        # PermissionDenied
        if isinstance(exception, PermissionDenied):
            return JsonResponse({'error': 'Permission refusée', 'code': 'permission_denied'}, status=403)

        # Validation Django
        if isinstance(exception, DjangoValidationError):
            details = getattr(exception, 'message_dict', str(exception))
            return JsonResponse({
                'error': 'Données invalides',
                'details': details,
                'code': 'validation_error'
            }, status=400)

        # Validation DRF
        if isinstance(exception, DRFValidationError):
            return JsonResponse({
                'error': 'Données invalides',
                'details': exception.detail,
                'code': 'validation_error'
            }, status=400)

        # Exceptions DRF génériques
        if isinstance(exception, APIException):
            detail = exception.detail if hasattr(exception, 'detail') else str(exception)
            code = getattr(exception, 'default_code', 'api_error')
            return JsonResponse({'error': detail, 'code': code}, status=exception.status_code)

        # Erreur serveur générique
        return JsonResponse({'error': 'Erreur interne', 'code': 'server_error'}, status=500)
