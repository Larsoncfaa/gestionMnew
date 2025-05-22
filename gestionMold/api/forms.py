# api/forms.py

from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, AuthenticationForm
from django.core.exceptions import ValidationError
from django.utils import timezone

from ai.services import predict_sales  # ou from .ai.services import predict_sales
from .models import (
    CustomUser, Payment, Product, Order, Delivery,
    Supplier, Warehouse, Batch, StockLevel, StockMovement,
    Invoice, ReturnRequest, ExchangeRequest, Notification,
    PromoCode, ProductDiscount, PaymentLog, TrackingInfo,
    Proof, StockAlert, ProductReview, ClientProfile, LoyaltyProgram
)


# ── UTILISATEURS ────────────────────────────────────────────────────────────────

class CustomUserRegistrationForm(UserCreationForm):
    email = forms.EmailField(label="Adresse e-mail", help_text="Requise et unique")
    class Meta:
        model = CustomUser
        fields = [
            'first_name', 'last_name', 'email',
            'password1', 'password2', 'is_agriculteur', 'is_livreur'
        ]
    def clean_email(self):
        e = self.cleaned_data['email'].lower()
        if CustomUser.objects.filter(email=e).exists():
            raise ValidationError("Cet email est déjà utilisé.")
        return e
    def clean(self):
        c = super().clean()
        if not (c.get('is_agriculteur') or c.get('is_livreur')):
            raise ValidationError("Vous devez cocher au moins un rôle.")
        return c


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = (
            'first_name', 'last_name', 'email',
            'is_agriculteur', 'is_livreur',
            'is_active', 'is_staff', 'is_superuser',
            'groups', 'user_permissions',
        )


class LoginForm(AuthenticationForm):
    username = forms.CharField(label="Nom d'utilisateur",
        widget=forms.TextInput(attrs={'style': 'font-size:1.2em;'}))
    password = forms.CharField(label="Mot de passe",
        widget=forms.PasswordInput(attrs={'style': 'font-size:1.2em;'}))


# ── PRODUITS ────────────────────────────────────────────────────────────────────

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'name','category','description','image',
            'quantity_in_stock','unit','purchase_price',
            'selling_price','expiration_date'
        ]
    def clean_quantity_in_stock(self):
        q = self.cleaned_data['quantity_in_stock']
        if q < 0: raise ValidationError("La quantité ne peut pas être négative.")
        return q
    def clean_expiration_date(self):
        d = self.cleaned_data.get('expiration_date')
        if d and d < timezone.now().date():
            raise ValidationError("La date d'expiration ne peut pas être passée.")
        return d


# ── COMMANDES ──────────────────────────────────────────────────────────────────

class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['client','order_status','total']
    def clean_total(self):
        t = self.cleaned_data['total']
        if t <= 0: raise ValidationError("Le total doit être > 0.")
        return t


# ── LIVRAISON ──────────────────────────────────────────────────────────────────

class DeliveryForm(forms.ModelForm):
    class Meta:
        model = Delivery
        fields = ['deliverer','order','product','type','delivery_status','description']


# ── FOURNISSEURS ───────────────────────────────────────────────────────────────

class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ['name','contact','product_type','address']


# ── INVENTAIRE ─────────────────────────────────────────────────────────────────

class WarehouseForm(forms.ModelForm):
    class Meta:
        model = Warehouse
        fields = ['name','location']


class BatchForm(forms.ModelForm):
    class Meta:
        model = Batch
        fields = ['product','lot_number','expiration_date']


class StockLevelForm(forms.ModelForm):
    class Meta:
        model = StockLevel
        fields = ['product','warehouse','quantity']


class StockMovementForm(forms.ModelForm):
    class Meta:
        model = StockMovement
        fields = ['product','warehouse','batch','movement_type','quantity']


# ── FACTURES ET RETOURS ──────────────────────────────────────────────────────────

class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = ['order','pdf']


class ReturnRequestForm(forms.ModelForm):
    class Meta:
        model = ReturnRequest
        fields = ['order_line','reason','quantity']


class ExchangeRequestForm(forms.ModelForm):
    class Meta:
        model = ExchangeRequest
        fields = ['return_request','replacement','exchange_status']


# ── NOTIFICATIONS & PROMOS ──────────────────────────────────────────────────────

class NotificationForm(forms.ModelForm):
    class Meta:
        model = Notification
        fields = ['user','message','link','read']


class PromoCodeForm(forms.ModelForm):
    class Meta:
        model = PromoCode
        fields = ['code','discount_percent','valid_from','valid_to','usage_limit']


class ProductDiscountForm(forms.ModelForm):
    class Meta:
        model = ProductDiscount
        fields = ['product','discount_percent']


# ── PAIEMENTS & LOGS ────────────────────────────────────────────────────────────

class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['order','method','amount','payment_status']


class PaymentLogForm(forms.ModelForm):
    class Meta:
        model = PaymentLog
        fields = ['order','payment_status','amount','info']


# ── LIVRAISON – SUIVI ────────────────────────────────────────────────────────────

class TrackingInfoForm(forms.ModelForm):
    class Meta:
        model = TrackingInfo
        fields = ['delivery','tracking_status','location']


class ProofForm(forms.ModelForm):
    class Meta:
        model = Proof
        fields = ['delivery','image']


# ── ALERTES & AVIS ───────────────────────────────────────────────────────────────

class StockAlertForm(forms.ModelForm):
    class Meta:
        model = StockAlert
        fields = ['product','threshold','is_active']


class ProductReviewForm(forms.ModelForm):
    class Meta:
        model = ProductReview
        fields = ['client','product','rating','comment']


# ── FIDÉLITÉ ─────────────────────────────────────────────────────────────────────

class LoyaltyProgramForm(forms.ModelForm):
    class Meta:
        model = LoyaltyProgram
        fields = ['client','points']
    def clean_points(self):
        p = self.cleaned_data['points']
        if p < 0: raise ValidationError("Les points ne peuvent pas être négatifs.")
        return p


# ── IA – PRÉDICTION DES VENTES ─────────────────────────────────────────────────

class SalesPredictionForm(forms.Form):
    product_id = forms.IntegerField(label="Produit (ID)", min_value=1)
    history_days = forms.IntegerField(label="Jours d'historique", min_value=1, initial=30)

    def clean_product_id(self):
        pid = self.cleaned_data['product_id']
        if not Product.objects.filter(pk=pid).exists():
            raise ValidationError("Produit invalide.")
        return pid

    def predict(self):
        if not self.is_valid():
            raise ValidationError("Formulaire invalide.")
        data = {
            'product_id': self.cleaned_data['product_id'],
            'history_days': self.cleaned_data['history_days']
        }
        return predict_sales(data)
