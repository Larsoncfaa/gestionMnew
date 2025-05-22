from datetime import timedelta

from django.utils import timezone
from django.contrib.auth.password_validation import validate_password
from django.db import transaction, IntegrityError
from django.db.models import Q, Sum
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import extend_schema_field

from .models import (
    CustomUser, Category, Product, Supplier,
    Warehouse, Batch, StockLevel, StockMovement,
    ClientProfile, Order, OrderLine, Invoice,
    ReturnRequest, ExchangeRequest, Notification,
    PromoCode, ProductDiscount, PaymentLog, Payment,
    Delivery, TrackingInfo, Proof,
    StockAlert, ProductReview, RefundRequest,
    LoyaltyProgram,
)

User = get_user_model()


# ----------- User serializers -----------

class RegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = CustomUser
        fields = ('first_name', 'last_name', 'email', 'password')

    def validate_email(self, value):
        if CustomUser.objects.filter(email=value.lower()).exists():
            raise serializers.ValidationError(_("Email déjà utilisé"))
        return value.lower()

    def create(self, validated_data):
        user = CustomUser(
            email=validated_data['email'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name']
        )
        user.set_password(validated_data['password'])
        user.save()
        return user


class LoginSerializer(serializers.Serializer):
    login = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        login = data['login'].lower()
        password = data['password']
        user = CustomUser.objects.filter(Q(email=login) | Q(username=login)).first()
        if not user or not user.check_password(password):
            raise serializers.ValidationError(_("Identifiants invalides"))
        if not user.is_verified:
            raise serializers.ValidationError(_("Compte non vérifié"))
        data['user'] = user
        return data


# ----------- Core serializers -----------

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']


class ProductSerializer(serializers.ModelSerializer):
    category = serializers.CharField()
    image = serializers.ImageField(required=False)

    class Meta:
        model = Product
        fields = '__all__'

    def validate_category(self, value):
        cat, _ = Category.objects.get_or_create(name=value)
        return cat


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = ['id', 'name', 'contact', 'product_type', 'address', 'date_added']


# ----------- Inventory serializers -----------

class WarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warehouse
        fields = ['id', 'name', 'location']


class BatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Batch
        fields = ['id', 'product', 'lot_number', 'expiration_date']


class StockLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockLevel
        fields = ['id', 'product', 'warehouse', 'quantity']


class StockMovementSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockMovement
        fields = ['id', 'product', 'warehouse', 'batch', 'movement_type', 'quantity', 'timestamp', 'user']


# ----------- Client & order serializers -----------

class ClientProfileSerializer(serializers.ModelSerializer):
    points = serializers.IntegerField(source='loyalty.points', read_only=True)

    class Meta:
        model = ClientProfile
        fields = ['id', 'user', 'location', 'balance', 'points']


class OrderLineSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)

    class Meta:
        model = OrderLine
        fields = ['id', 'product', 'quantity', 'unit_price']
        read_only_fields = ['unit_price']

class OrderLineWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderLine
        fields = ['product', 'quantity',]

    def create(self, validated_data):
        lines_data = validated_data.pop('lines')
        with transaction.atomic():
            order = Order.objects.create(**validated_data)
            for ln in lines_data:
                OrderLine.objects.create(order=order, **ln)
        return order
    
class OrderSerializer(serializers.ModelSerializer):
    client = ClientProfileSerializer(read_only=True)
    lines = OrderLineSerializer(many=True)

    class Meta:
        model = Order
        fields = ['id', 'client', 'date_ordered', 'order_status', 'total', 'lines']


class OrderWriteSerializer(serializers.ModelSerializer):
    lines = OrderLineWriteSerializer(many=True)

    class Meta:
        model = Order
        fields = ['client', 'order_status', 'lines']

    def create(self, validated_data):
        lines_data = validated_data.pop('lines')
        with transaction.atomic():
            order = Order.objects.create(**validated_data)
            for ln in lines_data:
                OrderLine.objects.create(order=order, **ln)
        return order


class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = ['id', 'order', 'pdf', 'issued_at']


class ReturnRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReturnRequest
        fields = ['id', 'order_line', 'reason', 'quantity', 'approved', 'processed_at']


class ExchangeRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExchangeRequest
        fields = ['id', 'return_request', 'replacement', 'exchange_status']


# ----------- Notifications & promotions -----------

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'user', 'message', 'link', 'read', 'created_at']


class PromoCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromoCode
        fields = ['id', 'code', 'discount_percent', 'valid_from', 'valid_to', 'usage_limit']


class ProductDiscountSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductDiscount
        fields = ['id', 'product', 'discount_percent']


# ----------- Payments & deliveries -----------

class PaymentLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentLog
        fields = ['id', 'order', 'attempt_time', 'payment_status', 'amount', 'info']


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['id', 'order', 'method', 'amount', 'payment_status', 'paid_at']

    def validate(self, data):
        order = data['order']
        client_profile = order.client
        if data['method'] == 'BALANCE':
            if client_profile.balance < data['amount']:
                raise serializers.ValidationError(_("Solde insuffisant"))
        paid = order.payments.filter(payment_status='PAID').aggregate(sum=Sum('amount'))['sum'] or 0
        if data['amount'] > (order.total - paid):
            raise serializers.ValidationError(_("Montant supérieur au solde dû"))
        return data

    def create(self, validated_data):
        payment = super().create(validated_data)
        if payment.method == 'BALANCE' and payment.payment_status == 'PAID':
            client_profile = payment.order.client
            client_profile.balance -= payment.amount
            client_profile.save(update_fields=['balance'])
        return payment
        
        


class TrackingInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrackingInfo
        fields = ['id', 'delivery', 'tracking_status', 'location', 'timestamp']


class ProofSerializer(serializers.ModelSerializer):
    class Meta:
        model = Proof
        fields = ['id', 'delivery', 'image', 'uploaded_at']


class DeliverySerializer(serializers.ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all(), required=False),
    order = serializers.PrimaryKeyRelatedField(queryset=Order.objects.all())

    class Meta:
        model = Delivery
        fields = ['id', 'deliverer', 'order', 'product', 'type', 'delivery_status', 'description', 'created_at', 'updated_at']


# ----------- Stock alerts, reviews, refunds, loyalty -----------

class StockAlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockAlert
        fields = ['id', 'product', 'threshold', 'is_active']


class ProductReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductReview
        fields = ['id', 'client', 'product', 'rating', 'comment', 'created_at', 'verified_purchase']

    def validate(self, data):
        if not Order.objects.filter(client=data['client'], lines__product=data['product'], order_status=Order.DELIVERED).exists():
            raise serializers.ValidationError(_("Le client doit avoir acheté ce produit"))
        data['verified_purchase'] = True
        return data


class RefundRequestSerializer(serializers.ModelSerializer):
    days_remaining = serializers.SerializerMethodField()

    class Meta:
        model = RefundRequest
        fields = '__all__'
        read_only_fields = ('refund_status', 'requested_at', 'processed_at')

    @extend_schema_field(int)  # 👈 Swagger saura que ça retourne un entier
    def get_days_remaining(self, obj):
        if obj.order.order_status != Order.DELIVERED:
            return 0
        delta = (obj.order.date_ordered + timedelta(days=14)) - timezone.now()
        return max(delta.days, 0)

    def validate_evidence(self, value):
        max_size = 2 * 1024 * 1024  # 2 Mo
        if value.size > max_size:
            raise serializers.ValidationError("Fichier trop volumineux (max 2 Mo)")
        return value


class LoyaltyProgramSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoyaltyProgram
        fields = ['id', 'client', 'points', 'last_updated', 'transactions']
        read_only_fields = ['points', 'last_updated', 'transactions']


# ----------- Analytics input serializers -----------

class DeliveryInputSerializer(serializers.Serializer):
    client = serializers.DictField(
        child=serializers.FloatField(),
        help_text="Dictionnaire contenant 'lat' et 'lng' du client"
    )
    total_quantity = serializers.IntegerField(
        min_value=0,
        help_text="Quantité totale commandée pour l'estimation"
    )


class InventoryInputSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(help_text="ID du produit")
    window_days = serializers.IntegerField(
        default=30, min_value=1,
        help_text="Nombre de jours passés pour la prédiction de stock"
    )


class SalesInputSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(help_text="ID du produit")
    history_days = serializers.IntegerField(
        default=30, min_value=1,
        help_text="Nombre de jours d'historique de ventes à considérer"
    )
    forecast_days = serializers.IntegerField(
        default=30, min_value=1,
        help_text="Nombre de jours à prédire"
    )


class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'is_verified', 'is_agriculteur', 'is_livreur', 'is_client', 'language'
        ]
        read_only_fields = ['id', 'username', 'is_verified', 'is_agriculteur', 'is_livreur', 'is_client']


class LogoutSerializer(serializers.Serializer):
    # Aucun champ requis si c’est juste une déconnexion
    message = serializers.CharField(read_only=True)

class DeliveryPredictSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField()

    prediction = serializers.CharField(read_only=True)

class InventoryPredictSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    days = serializers.IntegerField()

    predicted_inventory = serializers.IntegerField(read_only=True)

class SalesPredictSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    period = serializers.CharField()  # exemple : '7_days', '1_month', etc.

    predicted_sales = serializers.IntegerField(read_only=True)


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']