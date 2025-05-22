from datetime import timedelta
from random import randint

from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Sum
from django.utils import timezone
from django.utils.translation import gettext as _

from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny

from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema, OpenApiResponse

from ai.predictors.sales_predictor import SalesPredictor
from ai.services import predict_delivery, predict_inventory, predict_sales

from .models import (
    CustomUser, Product, Supplier, Order, OrderLine,
    ClientProfile as Client, Category, ProductReview, RefundRequest,
    LoyaltyProgram, Delivery, Payment, Warehouse, Batch,
    StockLevel, StockMovement, Invoice, ReturnRequest,
    ExchangeRequest, Notification, PromoCode, ProductDiscount,
    PaymentLog, TrackingInfo, Proof, StockAlert
)
from .serializers import (
    RegistrationSerializer, LoginSerializer, ProductSerializer,
    DeliverySerializer, SupplierSerializer, OrderSerializer,
    OrderLineSerializer, OrderWriteSerializer, CategorySerializer,
    ProductReviewSerializer, RefundRequestSerializer, LoyaltyProgramSerializer,
    PaymentSerializer, WarehouseSerializer, BatchSerializer,
    StockLevelSerializer, StockMovementSerializer, InvoiceSerializer,
    ReturnRequestSerializer, ExchangeRequestSerializer,
    NotificationSerializer, PromoCodeSerializer, ProductDiscountSerializer,
    PaymentLogSerializer, TrackingInfoSerializer, ProofSerializer,
    StockAlertSerializer, ClientProfileSerializer as ClientSerializer,
    DeliveryInputSerializer, InventoryInputSerializer,
    SalesInputSerializer, CustomUserSerializer,
    LogoutSerializer, DeliveryPredictSerializer,
    InventoryPredictSerializer, SalesPredictSerializer, ProfileSerializer
)
from .permissions import IsAdminOrDelivererOrOrderOwner
from django.shortcuts import render


# ----------- Authentification -----------

class RegistrationAPI(APIView):
    permission_classes = [AllowAny]
    serializer_class = RegistrationSerializer

    @extend_schema(
        request=RegistrationSerializer,
        responses={201: OpenApiResponse(response=RegistrationSerializer)}
    )
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': {'id': user.id, 'username': user.username, 'email': user.email}
        }, status=status.HTTP_201_CREATED)


class LoginAPI(APIView):
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    @extend_schema(
        request=LoginSerializer,
        responses={200: OpenApiResponse(response=LoginSerializer)}
    )
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
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

    @extend_schema(
        request=ProductSerializer,
        responses={201: OpenApiResponse(response=ProductSerializer)}
    )
    def perform_create(self, serializer):
        try:
            serializer.save()
        except ValidationError as e:
            raise PermissionDenied(e.message_dict)


# ----------- Livraisons -----------

class DeliveryViewSet(viewsets.ModelViewSet):
    queryset = Delivery.objects.select_related('order', 'deliverer').all()
    serializer_class = DeliverySerializer
    permission_classes = [IsAdminOrDelivererOrOrderOwner]

    @action(detail=True, methods=['post'])
    @extend_schema(
        responses={200: OpenApiResponse(description="Livraison marquée terminée")}
    )
    def mark_finished(self, request, pk=None):
        delivery = self.get_object()
        delivery.status = Delivery.Status.TERMINEE
        delivery.save(update_fields=['status'])
        return Response({'status': delivery.status})

    @action(detail=True, methods=['post'], serializer_class=DeliveryPredictSerializer)
    @extend_schema(
        request=DeliveryInputSerializer,
        responses={200: OpenApiResponse(response=DeliveryPredictSerializer)}
    )
    def predict(self, request, pk=None):
        delivery = self.get_object()
        data = {
            'client': {'lat': 0.0, 'lng': 0.0},
            'total_quantity': sum(line.quantity for line in delivery.order.lines.all())
        }
        prediction = predict_delivery(data)
        return Response({'prediction': prediction})


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
    @extend_schema(
        responses={200: OpenApiResponse(description="Prédiction de ventes")}
    )
    def predict_sales(self, request, pk=None):
        order = self.get_object()
        prediction = SalesPredictor().predict(order)
        return Response({'prediction': prediction})


# ----------- Dashboard -----------

class DashboardView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = None

    @extend_schema(
        responses={200: OpenApiResponse(description="Données du dashboard", response=dict)}
    )
    def get(self, request):
        total_stock = Product.objects.aggregate(total=Sum('quantity_in_stock'))['total'] or 0
        expiring_soon = Product.objects.filter(
            expiration_date__range=(timezone.now(), timezone.now() + timedelta(days=7))
        ).count()
        sales_trend = {
            (timezone.now() - timedelta(days=i)).strftime('%Y-%m-%d'): randint(0, 100)
            for i in range(30)
        }
        return Response({
            'total_stock': total_stock,
            'expiring_soon': expiring_soon,
            'sales_trend': sales_trend
        })


# ----------- Prédictions IA générales -----------

class PredictionView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SalesInputSerializer

    @extend_schema(
        request=SalesInputSerializer,
        responses={200: OpenApiResponse(description="Prédiction", response=dict)}
    )
    def post(self, request):
        try:
            prediction = SalesPredictor().predict(request.data)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'prediction': prediction, 'model_version': '1.2.0'})


# ----------- IA spécifiques -----------

class DeliveryPredictView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = DeliveryInputSerializer

    @extend_schema(
        request=DeliveryInputSerializer,
        responses={200: OpenApiResponse(response=DeliveryPredictSerializer)}
    )
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(predict_delivery(serializer.validated_data))


class InventoryPredictView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = InventoryInputSerializer

    @extend_schema(
        request=InventoryInputSerializer,
        responses={200: OpenApiResponse(response=InventoryPredictSerializer)}
    )
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(predict_inventory(serializer.validated_data))


class SalesPredictView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SalesInputSerializer

    @extend_schema(
        request=SalesInputSerializer,
        responses={200: OpenApiResponse(response=SalesPredictSerializer)}
    )
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(predict_sales(serializer.validated_data))


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

    @extend_schema(responses={200: OpenApiResponse(response=LoyaltyProgramSerializer)})
    def get(self, request):
        return Response(request.user.client_profile.loyalty.serialize())


class LoyaltyProgramListCreateAPIView(generics.ListCreateAPIView):
    queryset = LoyaltyProgram.objects.all()
    serializer_class = LoyaltyProgramSerializer
    permission_classes = [IsAuthenticated]
   


class PaymentCreateView(generics.CreateAPIView):
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    @extend_schema(request=PaymentSerializer, responses={201: OpenApiResponse(response=PaymentSerializer)})
    def post(self, request):
        return super().post(request)


class LoyaltyUsePointsView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = None

    @extend_schema(request=None, responses={200: OpenApiResponse(description='Points utilisés', response=dict)})
    def post(self, request):
        points = int(request.data.get('points', 0))
        loyalty = request.user.client_profile.loyalty
        try:
            loyalty.use_points(points)
            return Response({'success': True, 'new_balance': loyalty.points})
        except ValidationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class LoyaltyHistoryView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = None

    @extend_schema(responses={200: OpenApiResponse(description='Historique fidélité', response=dict)})
    def get(self, request):
        return Response(request.user.client_profile.loyalty.transactions)


# ----------- CRUD génériques (reste des entités) -----------

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


class WarehouseListCreateAPIView(generics.ListCreateAPIView):
    queryset = Warehouse.objects.all()
    serializer_class = WarehouseSerializer
    permission_classes = [IsAuthenticated]
   


class WarehouseDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Warehouse.objects.all()
    serializer_class = WarehouseSerializer
    permission_classes = [IsAuthenticated]


class BatchListCreateAPIView(generics.ListCreateAPIView):
    queryset = Batch.objects.all()
    serializer_class = BatchSerializer
    permission_classes = [IsAuthenticated]
    


class BatchDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Batch.objects.all()
    serializer_class = BatchSerializer
    permission_classes = [IsAuthenticated]


class StockLevelListCreateAPIView(generics.ListCreateAPIView):
    queryset = StockLevel.objects.all()
    serializer_class = StockLevelSerializer
    permission_classes = [IsAuthenticated]
    


class StockLevelDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = StockLevel.objects.all()
    serializer_class = StockLevelSerializer
    permission_classes = [IsAuthenticated]


class StockMovementListCreateAPIView(generics.ListCreateAPIView):
    queryset = StockMovement.objects.all()
    serializer_class = StockMovementSerializer
    permission_classes = [IsAuthenticated]
    


class StockMovementDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = StockMovement.objects.all()
    serializer_class = StockMovementSerializer
    permission_classes = [IsAuthenticated]


class InvoiceListCreateAPIView(generics.ListCreateAPIView):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]
   


class InvoiceDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Invoice.objects.all()
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]


class ReturnRequestListCreateAPIView(generics.ListCreateAPIView):
    queryset = ReturnRequest.objects.all()
    serializer_class = ReturnRequestSerializer
    permission_classes = [IsAuthenticated]
    


class ReturnRequestDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ReturnRequest.objects.all()
    serializer_class = ReturnRequestSerializer
    permission_classes = [IsAuthenticated]


class ExchangeRequestListCreateAPIView(generics.ListCreateAPIView):
    queryset = ExchangeRequest.objects.all()
    serializer_class = ExchangeRequestSerializer
    permission_classes = [IsAuthenticated]
    


class ExchangeRequestDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ExchangeRequest.objects.all()
    serializer_class = ExchangeRequestSerializer
    permission_classes = [IsAuthenticated]


class NotificationListCreateAPIView(generics.ListCreateAPIView):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    


class NotificationDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]


class PromoCodeListCreateAPIView(generics.ListCreateAPIView):
    queryset = PromoCode.objects.all()
    serializer_class = PromoCodeSerializer
    permission_classes = [IsAuthenticated]
    


class PromoCodeDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = PromoCode.objects.all()
    serializer_class = PromoCodeSerializer
    permission_classes = [IsAuthenticated]


class ProductDiscountListCreateAPIView(generics.ListCreateAPIView):
    queryset = ProductDiscount.objects.all()
    serializer_class = ProductDiscountSerializer
    permission_classes = [IsAuthenticated]
   


class ProductDiscountDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = ProductDiscount.objects.all()
    serializer_class = ProductDiscountSerializer
    permission_classes = [IsAuthenticated]


class PaymentLogListCreateAPIView(generics.ListCreateAPIView):
    queryset = PaymentLog.objects.all()
    serializer_class = PaymentLogSerializer
    permission_classes = [IsAuthenticated]
    


class PaymentLogDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = PaymentLog.objects.all()
    serializer_class = PaymentLogSerializer
    permission_classes = [IsAuthenticated]


class TrackingInfoListCreateAPIView(generics.ListCreateAPIView):
    queryset = TrackingInfo.objects.all()
    serializer_class = TrackingInfoSerializer
    permission_classes = [IsAuthenticated]
    


class TrackingInfoDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = TrackingInfo.objects.all()
    serializer_class = TrackingInfoSerializer
    permission_classes = [IsAuthenticated]


class ProofListCreateAPIView(generics.ListCreateAPIView):
    queryset = Proof.objects.all()
    serializer_class = ProofSerializer
    permission_classes = [IsAuthenticated]
   

class ProofDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Proof.objects.all()
    serializer_class = ProofSerializer
    permission_classes = [IsAuthenticated]


class StockAlertListCreateAPIView(generics.ListCreateAPIView):
    queryset = StockAlert.objects.all()
    serializer_class = StockAlertSerializer
    permission_classes = [IsAuthenticated]
    


class StockAlertDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = StockAlert.objects.all()
    serializer_class = StockAlertSerializer
    permission_classes = [IsAuthenticated]


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = LogoutSerializer

    @extend_schema(
        request=LogoutSerializer,
        responses={205: OpenApiResponse(response=LogoutSerializer)}
    )
    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"message": "Déconnexion réussie."}, status=status.HTTP_205_RESET_CONTENT)
        except Exception:
            return Response({"error": "Token invalide ou déjà blacklisté."}, status=status.HTTP_400_BAD_REQUEST)


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ProfileSerializer

    @extend_schema(
        responses={200: OpenApiResponse(response=ProfileSerializer)}
    )
    def get(self, request):
        serializer = self.serializer_class(request.user)
        return Response(serializer.data)

    @extend_schema(
        request=ProfileSerializer,
        responses={200: OpenApiResponse(response=ProfileSerializer)}
    )
    def put(self, request):
        serializer = self.serializer_class(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


# ----------- Vue de test HTML -----------

def test_accueil(request):
    return render(request, 'accueil.html')
