# api/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html

from .models import (
    CustomUser, Category, Product, Delivery, Order, OrderLine,
    Payment, ReturnRequest, Supplier, ClientProfile, ProductReview, RefundRequest,
    ExchangeRequest, LoyaltyProgram, Warehouse, Batch, StockLevel, StockMovement,
    Invoice, Notification, PromoCode, ProductDiscount,
    PaymentLog, TrackingInfo, Proof, StockAlert
)
from .forms import CustomUserRegistrationForm, CustomUserChangeForm


# ─── Utilisateur personnalisé ─────────────────────────────────────────────────────
@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin):
    add_form = CustomUserRegistrationForm
    form = CustomUserChangeForm
    model = CustomUser

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Informations personnelles', {
            'fields': ('first_name', 'last_name', 'email','is_client', 'is_agriculteur', 'is_livreur')
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
        ('Dates', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'username', 'email',
                'password1', 'password2','is_client',
                'is_agriculteur', 'is_livreur',
                'is_staff', 'is_active'
            ),
        }),
    )

    list_display = ('username', 'email', 'is_staff', 'is_active', 'is_client', 'is_agriculteur', 'is_livreur')
    list_filter = ('is_staff', 'is_active', 'is_client', 'is_agriculteur', 'is_livreur')
    search_fields = ('username', 'email')
    ordering = ('username',)
    readonly_fields = ('last_login', 'date_joined')


# ─── Catégories de produit ───────────────────────────────────────────────────────
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)
    ordering = ('name',)


# ─── Produits ─────────────────────────────────────────────────────────────────────
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'name', 'category', 'quantity_in_stock', 'unit',
        'selling_price', 'qr_code_preview'
    )
    search_fields = ('name',)
    list_filter = ('category',)
    readonly_fields = ('qr_code_preview',)
    autocomplete_fields = ['category']
    ordering = ('name',)

    def qr_code_preview(self, obj):
        if obj.qr_code_image:
            return format_html('<img src="{}" width="100"/>', obj.qr_code_image.url)
        return "—"
    qr_code_preview.short_description = "QR Code"


# ─── Lignes de commande (inline) ─────────────────────────────────────────────────
class OrderLineInline(admin.TabularInline):
    model = OrderLine
    extra = 0
    autocomplete_fields = ['product']


# ─── Commandes ───────────────────────────────────────────────────────────────────
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'client_username', 'date_ordered', 'order_status', 'total')
    list_filter = ('order_status', 'date_ordered')
    search_fields = ('id', 'client__user__username')
    autocomplete_fields = ['client']
    inlines = [OrderLineInline]
    ordering = ('-date_ordered',)
    readonly_fields = ('total',)

    def client_username(self, obj):
        return obj.client.user.username if obj.client and obj.client.user else "—"
    client_username.short_description = "Client"


@admin.register(OrderLine)
class OrderLineAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'product', 'quantity', 'unit_price')
    search_fields = ('order__id', 'product__name')
    autocomplete_fields = ['order', 'product']
    ordering = ('order',)
    readonly_fields = ('unit_price',)


# ─── Paiements ───────────────────────────────────────────────────────────────────
@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'method', 'amount', 'payment_status', 'paid_at')
    search_fields = ('order__id',)
    list_filter = ('method', 'payment_status')
    autocomplete_fields = ['order']
    ordering = ('-paid_at',)


# ─── Fournisseurs ────────────────────────────────────────────────────────────────
@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'product_type')
    search_fields = ('name',)
    ordering = ('name',)


# ─── Clients ─────────────────────────────────────────────────────────────────────
@admin.register(ClientProfile)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'location', 'balance')
    search_fields = ('user__username',)
    autocomplete_fields = ['user']
    ordering = ('user__username',)


# ─── Avis produits ───────────────────────────────────────────────────────────────
@admin.register(ProductReview)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'client', 'rating', 'created_at')
    list_filter = ('rating',)
    search_fields = ('product__name', 'client__user__username')
    autocomplete_fields = ['product', 'client']
    ordering = ('-created_at',)


# ─── Demandes de retour ───────────────────────────────────────────────────────────
@admin.register(ReturnRequest)
class ReturnRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'order_line', 'approved', 'reason', 'processed_at')
    list_filter = ('approved',)
    search_fields = ('order_line__order__id', 'order_line__product__name')
    autocomplete_fields = ['order_line']
    ordering = ('-requested_at',)


# ─── Échanges suite à retour ────────────────────────────────────────────────────
@admin.register(ExchangeRequest)
class ExchangeRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'return_request', 'replacement', 'exchange_status')
    list_filter = ('exchange_status',)
    autocomplete_fields = ['return_request', 'replacement']
    ordering = ('-id',)


# ─── Fidélité ────────────────────────────────────────────────────────────────────
@admin.register(LoyaltyProgram)
class LoyaltyAdmin(admin.ModelAdmin):
    list_display = ('id', 'client', 'points', 'last_updated')
    search_fields = ('client__user__username',)
    autocomplete_fields = ['client']
    ordering = ('-last_updated',)


# ─── Livraisons ──────────────────────────────────────────────────────────────────
@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = ('id', 'deliverer', 'order', 'product', 'type', 'delivery_status', 'created_at')
    list_filter = ('type', 'delivery_status')
    search_fields = ('description', 'order__id', 'product__name', 'deliverer__username')
    autocomplete_fields = ['deliverer', 'order', 'product']
    ordering = ('-created_at',)


# ─── Entrepôts ───────────────────────────────────────────────────────────────────
@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'location')
    search_fields = ('name', 'location')
    ordering = ('name',)


# ─── Lots (Batches) ─────────────────────────────────────────────────────────────
@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'lot_number', 'expiration_date')
    search_fields = ('product__name', 'lot_number')
    autocomplete_fields = ['product']
    ordering = ('product__name', 'lot_number')


# ─── Niveaux de stock ──────────────────────────────────────────────────────────
@admin.register(StockLevel)
class StockLevelAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'warehouse', 'quantity')
    list_filter = ('warehouse',)
    autocomplete_fields = ['product', 'warehouse']
    ordering = ('product__name',)


# ─── Mouvements de stock ───────────────────────────────────────────────────────
@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'warehouse', 'movement_type', 'quantity', 'timestamp', 'user')
    list_filter = ('movement_type', 'warehouse')
    autocomplete_fields = ['product', 'warehouse', 'batch', 'user']
    ordering = ('-timestamp',)


# ─── Factures ───────────────────────────────────────────────────────────────────
@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'issued_at')
    search_fields = ('order__id',)
    autocomplete_fields = ['order']
    ordering = ('-issued_at',)


# ─── Notifications internes ─────────────────────────────────────────────────────
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'message', 'link', 'read', 'created_at')
    list_filter = ('read',)
    search_fields = ('user__username', 'message')
    autocomplete_fields = ['user']
    ordering = ('-created_at',)


# ─── Codes promo ────────────────────────────────────────────────────────────────
@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = ('id', 'code', 'discount_percent', 'valid_from', 'valid_to', 'usage_limit')
    list_filter = ('valid_from', 'valid_to')
    search_fields = ('code',)
    ordering = ('code',)


# ─── Remises produit ────────────────────────────────────────────────────────────
@admin.register(ProductDiscount)
class ProductDiscountAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'discount_percent')
    search_fields = ('product__name',)
    autocomplete_fields = ['product']
    ordering = ('-discount_percent',)


# ─── Logs de paiement ──────────────────────────────────────────────────────────
@admin.register(PaymentLog)
class PaymentLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'attempt_time', 'payment_status', 'amount')
    list_filter = ('payment_status',)
    search_fields = ('order__id',)
    autocomplete_fields = ['order']
    ordering = ('-attempt_time',)


# ─── Suivi livraison ────────────────────────────────────────────────────────────
@admin.register(TrackingInfo)
class TrackingInfoAdmin(admin.ModelAdmin):
    list_display = ('id', 'delivery', 'tracking_status', 'location', 'timestamp')
    search_fields = ('delivery__id', 'tracking_status', 'location')
    autocomplete_fields = ['delivery']
    ordering = ('-timestamp',)


# ─── Preuves de livraison ───────────────────────────────────────────────────────
@admin.register(Proof)
class ProofAdmin(admin.ModelAdmin):
    list_display = ('id', 'delivery', 'uploaded_at')
    search_fields = ('delivery__id',)
    autocomplete_fields = ['delivery']
    ordering = ('-uploaded_at',)


# ─── Alertes de stock ───────────────────────────────────────────────────────────
@admin.register(StockAlert)
class StockAlertAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'threshold', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('product__name',)
    autocomplete_fields = ['product']
    ordering = ('-threshold',)
