# api/admin.py
from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import (
    CustomUser, Category, Product, Delivery, Order, OrderLine,
    Payment, Supplier, ClientProfile, ProductReview, RefundRequest,
    LoyaltyProgram
)
from .forms import CustomUserRegistrationForm, CustomUserChangeForm

@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin):
    add_form = CustomUserRegistrationForm
    form     = CustomUserChangeForm
    model    = CustomUser

    # ── pour l’édition d’un user (fieldsets) ──
    fieldsets = (
        (None, {'fields': ('username', 'password')}),         # <-- seulement 'password'
        ('Infos persos', {'fields': ('first_name','last_name','email','is_agriculteur','is_livreur')}),
        ('Permissions', {'fields': ('is_active','is_staff','is_superuser','groups','user_permissions')}),
        ('Dates', {'fields': ('last_login','date_joined')}),
    )

    # ── pour l’ajout d’un user (add_fieldsets) ──
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'username','email',
                'password1','password2',            # <-- password1/password2 UNIQUEMENT ici
                'is_agriculteur','is_livreur',
                'is_staff','is_active'
            ),
        }),
    )

    list_display    = ('username','email','is_staff','is_active')
    search_fields   = ('username','email')
    ordering        = ('username',)
    readonly_fields = ('last_login','date_joined')
    list_filter     = ('is_staff','is_active')
# Category Admin
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)

# Product Admin
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'category', 'quantity_in_stock', 'unit', 'selling_price', 'qr_code_preview')
    search_fields = ('name',)
    list_filter = ('category',)
    readonly_fields = ('qr_code_preview',)
    autocomplete_fields = ['category']

    def qr_code_preview(self, obj):
        if obj.qr_code_image:
            return format_html('<img src="{}" width="100"/>', obj.qr_code_image.url)
        return "—"
    qr_code_preview.short_description = "QR Code"

# OrderLine Inline
class OrderLineInline(admin.TabularInline):
    model = OrderLine
    extra = 0
    autocomplete_fields = ['product']

# Order Admin
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'client_username', 'date_ordered', 'status', 'total')
    list_filter = ('status', 'date_ordered')
    search_fields = ('id', 'client__user__username')
    autocomplete_fields = ['client']
    inlines = [OrderLineInline]

    def client_username(self, obj):
        return obj.client.user.username
    client_username.short_description = "Client"

# Payment Admin
@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'method', 'amount', 'status', 'paid_at')
    search_fields = ('order__id',)
    list_filter = ('method', 'status')

# Supplier Admin
@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'product_type')
    search_fields = ('name',)

# ClientProfile Admin
@admin.register(ClientProfile)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'location', 'balance')
    search_fields = ('user__username',)
    autocomplete_fields = ['user']

# ProductReview Admin
@admin.register(ProductReview)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'client', 'rating', 'created_at')
    list_filter = ('rating',)
    search_fields = ('product__name', 'client__user__username')
    autocomplete_fields = ['product', 'client']

# RefundRequest Admin
@admin.register(RefundRequest)
class RefundAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'status', 'requested_at')
    list_filter = ('status',)
    autocomplete_fields = ['order']

# LoyaltyProgram Admin
@admin.register(LoyaltyProgram)
class LoyaltyAdmin(admin.ModelAdmin):
    list_display = ('id', 'client', 'points', 'last_updated')
    search_fields = ('client__user__username',)
    autocomplete_fields = ['client']

# Delivery Admin
@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = ('id', 'deliverer', 'order', 'product', 'type', 'status', 'created_at')
    list_filter = ('type', 'status')
    search_fields = ('description', 'order__id', 'product__name', 'deliverer__username')
    autocomplete_fields = ['deliverer', 'order', 'product']


