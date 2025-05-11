# api/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

from .views import (
    RegistrationAPI, LoginAPI,
    ProductListCreateAPIView, SupplierListCreateAPIView, SupplierDetailAPIView,
    OrderViewSet, DashboardView, PredictionView,
    ProductReviewCreateView, RefundRequestCreateView,
    LoyaltyProgramDetailView, LoyaltyProgramListCreateAPIView,
    PaymentCreateView, OrderLineListCreateAPIView, OrderLineDetailAPIView,
    ClientListCreateAPIView, ClientDetailAPIView,
    CategoryListCreateAPIView, CategoryDetailAPIView,
    DeliveryPredictView, InventoryPredictView, SalesPredictView, DeliveryViewSet
)

# router pour les viewsets
router = DefaultRouter()
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'deliveries', DeliveryViewSet, basename='delivery')


# swagger / redoc
schema_view = get_schema_view(
   openapi.Info(
      title="API Gestion Agricole",
      default_version='v1',
      description="Documentation de l’API Gestion Agricole",
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    # –– Auth (inscription / connexion JWT)
    path('v1/auth/register/', RegistrationAPI.as_view(), name='v1-auth-register'),
    path('v1/auth/login/',    LoginAPI.as_view(),    name='v1-auth-login'),

    # –– CRUD Produits
    path('v1/products/', ProductListCreateAPIView.as_view(), name='v1-product-list-create'),


    # –– Fournisseurs
    path('v1/suppliers/',       SupplierListCreateAPIView.as_view(), name='v1-supplier-list-create'),
    path('v1/suppliers/<int:pk>/', SupplierDetailAPIView.as_view(),      name='v1-supplier-detail'),

    # –– Avis et remboursements
    path('v1/reviews/', ProductReviewCreateView.as_view(), name='v1-review-create'),
    path('v1/refunds/', RefundRequestCreateView.as_view(), name='v1-refund-create'),

    # –– Programme fidélité
    path('v1/loyalty/', LoyaltyProgramDetailView.as_view(),        name='v1-loyalty-detail'),
    path('v1/loyalty-programs/', LoyaltyProgramListCreateAPIView.as_view(), name='v1-loyaltyprogram-list'),

    # –– Paiements
    path('v1/payments/', PaymentCreateView.as_view(), name='v1-payment-create'),

    # –– Dashboard & prédictions globales IA
    path('v1/dashboard/', DashboardView.as_view(),   name='v1-dashboard'),
    path('v1/predict/',    PredictionView.as_view(), name='v1-prediction'),

    # –– Lignes de commande
    path('v1/order-lines/',      OrderLineListCreateAPIView.as_view(), name='v1-orderline-list'),
    path('v1/order-lines/<int:pk>/', OrderLineDetailAPIView.as_view(),     name='v1-orderline-detail'),

    # –– Clients
    path('v1/clients/',      ClientListCreateAPIView.as_view(),    name='v1-client-list'),
    path('v1/clients/<int:pk>/', ClientDetailAPIView.as_view(),    name='v1-client-detail'),

    # –– Catégories
    path('v1/categories/',      CategoryListCreateAPIView.as_view(),    name='v1-category-list'),
    path('v1/categories/<int:pk>/', CategoryDetailAPIView.as_view(),    name='v1-category-detail'),

    # –– Endpoints IA détaillés
    path('v1/predict/delivery/',   DeliveryPredictView.as_view(),   name='v1-predict-delivery'),
    path('v1/predict/inventory/',  InventoryPredictView.as_view(),  name='v1-predict-inventory'),
    path('v1/predict/sales/',      SalesPredictView.as_view(),      name='v1-predict-sales'),

    # –– inclusion des routers (orders, deliveries)
    path('v1/', include(router.urls)),

    # –– Documentation Swagger / ReDoc
    path('swagger<format>.json', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/',               schema_view.with_ui('swagger',   cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/',                 schema_view.with_ui('redoc',     cache_timeout=0), name='schema-redoc'),
]
