from datetime import timedelta
from random import randint

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError
from django.db.models import Sum, Q
from django.utils import timezone
from django.utils.translation import gettext as _

from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from rest_framework_simplejwt.tokens import RefreshToken

from ai.predictors.sales_predictor import SalesPredictor
from ai.services import predict_delivery, predict_inventory, predict_sales

from .models import (
    CustomUser, Product, Supplier, Order, OrderLine,
    ClientProfile as Client, Category, ProductReview, RefundRequest,
    LoyaltyProgram, Delivery
)
from .serializers import (
    RegistrationSerializer, LoginSerializer, ProductSerializer,
   DeliverySerializer, SupplierSerializer, OrderSerializer,
    OrderLineSerializer, CategorySerializer, ProductReviewSerializer,
    RefundRequestSerializer, LoyaltyProgramSerializer, PaymentSerializer,
    DeliveryInputSerializer, InventoryInputSerializer, SalesInputSerializer,
    ClientSerializer, OrderWriteSerializer
)
from .permissions import IsAdminOrDelivererOrOrderOwner


# ----------- Authentification -----------

class RegistrationAPI(APIView):
    permission_classes = []

    def post(self, request):
        serializer = RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': {'id': user.id, 'username': user.username, 'email': user.email}
        }, status=status.HTTP_201_CREATED)


class LoginAPI(APIView):
    permission_classes = []

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': {'id': user.id, 'username': user.username, 'email': user.email}
        })


# ----------- Pagination -----------

class ProductPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


# ----------- Produits -----------

class ProductListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = ProductPagination

    def get_queryset(self):
        return Product.objects.all()

    def perform_create(self, serializer):
        try:
            serializer.save()
        except ValidationError as e:
            raise PermissionDenied(e.message_dict)


# ----------- Interventions -----------

class DeliveryViewSet(viewsets.ModelViewSet):
    queryset = Delivery.objects.select_related('order', 'deliverer').all()
    serializer_class = DeliverySerializer  # Tu pourras aussi renommer ce serializer
    permission_classes = [IsAdminOrDelivererOrOrderOwner]

    @action(detail=True, methods=['post'])
    def mark_delivered(self, request, pk=None):
        delivery = self.get_object()
        delivery.mark_delivered()
        return Response({'status': delivery.status, 'actual_date': delivery.actual_date})

    @action(detail=True, methods=['post'])
    def predict_estimate(self, request, pk=None):
        delivery = self.get_object()
        data = {
            'client': {'lat': 0.0, 'lng': 0.0},
            'total_quantity': sum(line.quantity for line in delivery.order.lines.all())
        }
        result = predict_delivery(data)
        if 'prediction' in result:
            delivery.estimated_date = timezone.now() + timedelta(hours=result['prediction'])
            delivery.save()
        return Response(result)



# ----------- Fournisseurs -----------

class SupplierListCreateAPIView(generics.ListCreateAPIView):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [IsAuthenticated]


class SupplierDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [IsAuthenticated]


# ----------- Commandes -----------

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.prefetch_related('lines').all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return OrderWriteSerializer
        return OrderSerializer

    @action(detail=True, methods=['post'])
    def predict_delivery(self, request, pk=None):
        order = self.get_object()
        prediction = SalesPredictor().predict(order)
        return Response({'prediction': prediction})


# ----------- Dashboard -----------

class DashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        total_stock = Product.objects.aggregate(total=Sum('quantity_in_stock'))['total'] or 0
        expiring_soon = Product.objects.filter(
            expiration_date__range=(timezone.now(), timezone.now() + timedelta(days=7))
        ).count()
        sales_trend = {
            (timezone.now() - timedelta(days=i)).strftime('%Y-%m-%d'): randint(0, 100)
            for i in range(30)
        }
        return Response({'total_stock': total_stock, 'expiring_soon': expiring_soon, 'sales_trend': sales_trend})


# ----------- Prédiction IA générale -----------

class PredictionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            prediction = SalesPredictor().predict(request.data)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'prediction': prediction, 'model_version': '1.2.0'})


# ----------- Reviews / Refunds / Loyalty / Payments -----------

class ProductReviewCreateView(generics.CreateAPIView):
    queryset = ProductReview.objects.all()
    serializer_class = ProductReviewSerializer
    permission_classes = [IsAuthenticated]


class RefundRequestCreateView(generics.CreateAPIView):
    queryset = RefundRequest.objects.all()
    serializer_class = RefundRequestSerializer
    permission_classes = [IsAuthenticated]


class LoyaltyProgramDetailView(generics.RetrieveAPIView):
    serializer_class = LoyaltyProgramSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user.client_profile.loyalty


class PaymentCreateView(generics.CreateAPIView):
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        order = serializer.validated_data['order']
        if order.client != self.request.user.client_profile:
            raise PermissionDenied(_("Vous ne pouvez pas payer cette commande"))
        try:
            serializer.save(status='PAID', paid_at=timezone.now())
        except IntegrityError as e:
            raise PermissionDenied(str(e))


# ----------- OrderLines, Clients, Categories, LoyaltyPrograms -----------

class OrderLineListCreateAPIView(generics.ListCreateAPIView):
    queryset = OrderLine.objects.all()
    serializer_class = OrderLineSerializer
    permission_classes = [IsAuthenticated]


class OrderLineDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = OrderLine.objects.all()
    serializer_class = OrderLineSerializer
    permission_classes = [IsAuthenticated]


class ClientListCreateAPIView(generics.ListCreateAPIView):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    permission_classes = [IsAuthenticated]


class ClientDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    permission_classes = [IsAuthenticated]


class CategoryListCreateAPIView(generics.ListCreateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]


class CategoryDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]


class LoyaltyProgramListCreateAPIView(generics.ListCreateAPIView):
    queryset = LoyaltyProgram.objects.all()
    serializer_class = LoyaltyProgramSerializer
    permission_classes = [IsAuthenticated]

class DeliveryPredictView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        serializer = DeliveryInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(predict_delivery(serializer.validated_data))


class InventoryPredictView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        serializer = InventoryInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(predict_inventory(serializer.validated_data))


class SalesPredictView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        serializer = SalesInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(predict_sales(serializer.validated_data))


class DeliveryViewSet(viewsets.ModelViewSet):
    """
    CRUD sur les livraisons + action IA pour estimer la date.
    """
    queryset = Delivery.objects.select_related('order','deliverer').all()
    serializer_class = DeliverySerializer
    permission_classes = [IsAdminOrDelivererOrOrderOwner]

    @action(detail=True, methods=['post'])
    def mark_delivered(self, request, pk=None):
        delivery = self.get_object()
        delivery.mark_delivered()
        return Response({'status': delivery.status, 'actual_date': delivery.actual_date})

    @action(detail=True, methods=['post'])
    def predict_estimate(self, request, pk=None):
        delivery = self.get_object()
        # préparer input pour le service IA
        data = {
            'client': {'lat': 0.0, 'lng': 0.0},
            'total_quantity': sum(line.quantity for line in delivery.order.lines.all())
        }
        result = predict_delivery(data)
        if 'prediction' in result:
            delivery.estimated_date = timezone.now() + timedelta(hours=result['prediction'])
            delivery.save(update_fields=['estimated_date'])
        return Response(result)
    
from django.shortcuts import render

def test_accueil(request):
    return render(request, 'accueil.html')
