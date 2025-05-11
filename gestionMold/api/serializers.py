from datetime import timedelta
from random import randint

from django.utils import timezone
from django.contrib.auth.password_validation import validate_password
from django.db import transaction, IntegrityError
from django.db.models import Q
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from .models import (
    CustomUser, Product, Delivery, Supplier, Order, OrderLine,
    ClientProfile as Client, Category, ProductReview, RefundRequest,
    LoyaltyProgram, Payment
)
from .constants import CATEGORY_MAP

User = get_user_model()


# ----------- User Serializers -----------

class RegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, style={'input_type': 'password'}, validators=[validate_password]
    )

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
    password = serializers.CharField(style={'input_type': 'password'})

    def validate(self, data):
        login = data.get('login').lower()
        password = data.get('password')
        user = CustomUser.objects.filter(Q(email=login) | Q(username=login)).first()
        if not user or not user.check_password(password):
            raise serializers.ValidationError(_("Identifiants invalides"))
        if not user.is_verified:
            raise serializers.ValidationError(_("Compte non vérifié"))
        data['user'] = user
        return data


# ----------- Core Serializers -----------

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']


class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer()

    class Meta:
        model = Product
        fields = '__all__'

    def validate(self, data):
        name = data.get('name', getattr(self.instance, 'name', None))
        cat = data.get('category') or self.instance.category
        allowed = CATEGORY_MAP.get(cat.name, [])
        if name not in allowed:
            raise serializers.ValidationError({
                'name': _(f"Produit “{name}” invalide pour la catégorie “{cat.name}”. Autorisé : {allowed}")
            })
        return data


class ProductWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'

class DeliverySerializer(serializers.ModelSerializer):
    type = serializers.ChoiceField(choices=Delivery.Type.choices)
    status = serializers.ChoiceField(choices=Delivery.Status.choices, read_only=True)

    class Meta:
        model = Delivery
        fields = [
            'id', 'deliverer', 'order', 'product',
            'type', 'status', 'description',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['status', 'created_at', 'updated_at']

class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = ['id', 'name', 'contact', 'product_type', 'address', 'date_added']


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = ['id', 'user', 'location', 'balance']


# ----------- Order Serializers -----------

class OrderLineSerializer(serializers.ModelSerializer):
    product = ProductSerializer()

    class Meta:
        model = OrderLine
        fields = ['id', 'product', 'quantity', 'unit_price']


class OrderLineWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderLine
        fields = ['product', 'quantity', 'unit_price']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderLineSerializer(many=True, source='lines')
    client = ClientSerializer()

    class Meta:
        model = Order
        fields = ['id', 'client', 'date_ordered', 'status', 'total', 'items']


class OrderWriteSerializer(serializers.ModelSerializer):
    items = OrderLineWriteSerializer(many=True)

    class Meta:
        model = Order
        fields = ['client', 'status', 'items']

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        with transaction.atomic():
            order = Order.objects.create(**validated_data)
            for item in items_data:
                OrderLine.objects.create(order=order, **item)
        return order


# ----------- Review, Refund, Loyalty, Payment -----------

class ProductReviewSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.user.username', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = ProductReview
        fields = '__all__'
        read_only_fields = ('created_at', 'verified_purchase')

    def validate(self, data):
        client = data['client']
        product = data['product']
        if not Order.objects.filter(client=client, lines__product=product, status='DELIVERED').exists():
            raise serializers.ValidationError(_("Le client doit avoir acheté ce produit pour le noter"))
        data['verified_purchase'] = True
        return data


class RefundRequestSerializer(serializers.ModelSerializer):
    days_remaining = serializers.SerializerMethodField()

    class Meta:
        model = RefundRequest
        fields = '__all__'
        read_only_fields = ('status', 'requested_at', 'processed_at')

    def get_days_remaining(self, obj):
        if obj.order.status != 'DELIVERED':
            return 0
        delta = (obj.order.date_ordered + timedelta(days=14)) - timezone.now()
        return max(delta.days, 0)

    def validate_order(self, value):
        if value.status != 'DELIVERED':
            raise serializers.ValidationError(_("Seules les commandes livrées peuvent être remboursées"))
        return value


class LoyaltyProgramSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoyaltyProgram
        fields = '__all__'
        read_only_fields = ('points', 'last_updated', 'transactions')


class PaymentSerializer(serializers.ModelSerializer):
    remaining_balance = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = '__all__'
        read_only_fields = ('paid_at',)

    def get_remaining_balance(self, obj):
        paid = sum(p.amount for p in obj.order.payments.filter(status='PAID'))
        return float(obj.order.total - paid)

    def validate(self, data):
        order = data['order']
        amount = data['amount']
        paid = sum(p.amount for p in order.payments.filter(status='PAID'))
        if amount > (order.total - paid):
            raise serializers.ValidationError(_("Montant supérieur au solde dû"))
        return data

    def create(self, validated_data):
        try:
            with transaction.atomic():
                payment = Payment.objects.create(**validated_data)
                return payment
        except IntegrityError as e:
            raise serializers.ValidationError({"detail": str(e)})


class DeliveryInputSerializer(serializers.Serializer):
    client = serializers.DictField(child=serializers.FloatField())
    total_quantity = serializers.IntegerField()


class InventoryInputSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    current_stock = serializers.FloatField()
    lead_time = serializers.FloatField()
    sales_velocity = serializers.FloatField()
    seasonality_factor = serializers.FloatField()
    supplier_reliability = serializers.FloatField()


class SalesInputSerializer(serializers.Serializer):
    historique_ventes = serializers.FloatField()
    stock_disponible = serializers.FloatField()
    saison = serializers.IntegerField()
    prix = serializers.FloatField()
    promotion = serializers.FloatField()

