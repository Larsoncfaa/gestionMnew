import logging
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied, ValidationError as DjangoValidationError
from rest_framework.exceptions import APIException, ValidationError as DRFValidationError
from api.models import Product, Order, Supplier

logger = logging.getLogger(__name__)

class CustomExceptionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        logger.error(f"Exception at {request.path}: {exception}", exc_info=True)

        if isinstance(exception, Product.DoesNotExist):
            return JsonResponse({'error':'Produit non trouvé','code':'product_not_found'}, status=404)
        if isinstance(exception, Order.DoesNotExist):
            return JsonResponse({'error':'Commande non trouvée','code':'order_not_found'}, status=404)
        if isinstance(exception, Supplier.DoesNotExist):
            return JsonResponse({'error':'Fournisseur non trouvé','code':'supplier_not_found'}, status=404)
        if isinstance(exception, PermissionDenied):
            return JsonResponse({'error':'Permission refusée','code':'permission_denied'}, status=403)
        if isinstance(exception, DjangoValidationError):
            return JsonResponse({'error':'Données invalides','details':exception.message_dict,'code':'validation_error'}, status=400)
        if isinstance(exception, DRFValidationError):
            return JsonResponse({'error':'Données invalides','details':exception.detail,'code':'validation_error'}, status=400)
        if isinstance(exception, APIException):
            return JsonResponse({'error':exception.detail,'code':getattr(exception,'code','api_error')}, status=exception.status_code)

        # Exception générique si non gérée ci-dessus
        return JsonResponse({'error':'Erreur interne','code':'server_error'}, status=500)
