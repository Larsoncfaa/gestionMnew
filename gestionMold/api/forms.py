# api/forms.py
from datetime import timezone
from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, AuthenticationForm
from django.core.exceptions import ValidationError
from .models import CustomUser, Product, Order, Delivery
from ai.services import predict_sales

# ── UTILISATEURS ────────────────────────────────────────────────────────────────
class CustomUserRegistrationForm(UserCreationForm):
    """Formulaire d'inscription avec validation d’email et mots de passe."""
    email = forms.EmailField(label="Adresse e‑mail", help_text="Requise et unique")

    class Meta:
        model = CustomUser
        fields = [
            'first_name', 'last_name', 'email', 'username',
            'password1', 'password2', 'is_agriculteur', 'is_livreur'
        ]

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if CustomUser.objects.filter(email=email).exists():
            raise ValidationError("Cet email est déjà utilisé.")
        return email

    def clean(self):
        cleaned = super().clean()
        if not (cleaned.get('is_agriculteur') or cleaned.get('is_livreur')):
            raise ValidationError("Vous devez cocher au moins un rôle : agriculteur ou livreur.")
        return cleaned


class CustomUserChangeForm(UserChangeForm):
    """Formulaire de modification d’utilisateur."""
    class Meta:
        model = CustomUser
        fields = (
            'first_name', 'last_name', 'email', 'username',
            'is_agriculteur', 'is_livreur',
            'is_active', 'is_staff', 'is_superuser',
            'groups', 'user_permissions',
        )

class LoginForm(AuthenticationForm):
    """Formulaire de connexion stylé."""
    username = forms.CharField(
        label="Nom d'utilisateur",
        widget=forms.TextInput(attrs={'style':'font-size:1.2em;'})
    )
    password = forms.CharField(
        label="Mot de passe",
        widget=forms.PasswordInput(attrs={'style':'font-size:1.2em;'})
    )

# ── PRODUITS ────────────────────────────────────────────────────────────────────
class ProductForm(forms.ModelForm):
    """Formulaire de création / édition de produit, avec validation métier."""
    class Meta:
        model = Product
        fields = [
            'name', 'category', 'description', 'image',
            'quantity_in_stock', 'unit', 'purchase_price',
            'selling_price', 'expiration_date'
        ]

    def clean_quantity_in_stock(self):
        q = self.cleaned_data['quantity_in_stock']
        if q < 0:
            raise ValidationError("La quantité ne peut pas être négative.")
        return q

    def clean_expiration_date(self):
        date = self.cleaned_data.get('expiration_date')
        if date and date < timezone.now().date():
            raise ValidationError("La date d'expiration ne peut pas être passée.")
        return date

# ── COMMANDES ──────────────────────────────────────────────────────────────────
class OrderForm(forms.ModelForm):
    """Formulaire de création de commande."""
    class Meta:
        model = Order
        fields = ['client', 'status', 'total']

    def clean_total(self):
        total = self.cleaned_data['total']
        if total <= 0:
            raise ValidationError("Le total doit être supérieur à zéro.")
        return total

# ── LIVRAISON ──────────────────────────────────────────────────────────────────
class DeliveryForm(forms.ModelForm):
    """Formulaire d’affectation de livreur et suivi."""
    class Meta:
        model = Delivery
        # Champs alignés sur le modèle Delivery
        fields = ['deliverer', 'order', 'product', 'type', 'status', 'description']

# ── IA – PRÉDICTION DES VENTES ─────────────────────────────────────────────────
class SalesPredictionForm(forms.Form):
    """Formulaire simple pour déclencher une prédiction IA de ventes."""
    historique_ventes = forms.FloatField(label="Historique ventes", min_value=0)
    stock_disponible  = forms.FloatField(label="Stock disponible", min_value=0)
    saison            = forms.IntegerField(label="Saison (1-4)", min_value=1, max_value=4)
    prix              = forms.FloatField(label="Prix unitaire", min_value=0)
    promotion         = forms.FloatField(label="Taux promo (0‑1)", min_value=0, max_value=1)

    def clean(self):
        data = super().clean()
        return data

    def predict(self):
        if not self.is_valid():
            raise ValidationError("Formulaire invalide, impossible de prédire.")
        return predict_sales(self.cleaned_data)
