from django.contrib.auth.models import AbstractUser
from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from datetime import timedelta
import uuid, qrcode
from io import BytesIO
from PIL import Image
from django.core.files import File

from .constants import ALL_CATEGORIES, CATEGORY_MAP, UNIT_CHOICES
from .utils import send_alert


class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    language = models.CharField(max_length=5, default='fr')
    is_verified = models.BooleanField(default=False)
    is_agriculteur = models.BooleanField(default=False)
    is_livreur = models.BooleanField(default=False)

    REQUIRED_FIELDS = ['email', 'first_name', 'last_name']

    class Meta:
        verbose_name = _("Utilisateur")
        verbose_name_plural = _("Utilisateurs")

    def save(self, *args, **kwargs):
        if not self.username:
            if not self.pk and CustomUser.objects.filter(email=self.email).exists():
                raise ValidationError(_("Un utilisateur avec cet email existe déjà."))
            base = f"{self.first_name[0]}{self.last_name}".lower()
            self.username = f"{base}-{uuid.uuid4().hex[:4]}"
        super().save(*args, **kwargs)
    pass


class Category(models.Model):
    name = models.CharField(
        max_length=50,
        choices=[(c, c) for c in ALL_CATEGORIES],
        unique=True,
        verbose_name=_("Catégorie"),
        help_text=_("Choisir une catégorie parmi la liste standard")
    )

    class Meta:
        verbose_name = _("Catégorie")
        verbose_name_plural = _("Catégories")

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=100, verbose_name=_("Nom"))
    category = models.ForeignKey(Category, on_delete=models.PROTECT, verbose_name=_("Catégorie"))
    description = models.TextField(blank=True, null=True, verbose_name=_("Description"))
    image = models.ImageField(upload_to='products/', blank=True, null=True, verbose_name=_("Image"))
    quantity_in_stock = models.PositiveIntegerField(default=0, verbose_name=_("Quantité en stock"))
    unit = models.CharField(max_length=5, choices=UNIT_CHOICES, verbose_name=_("Unité"))
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("Prix d'achat"))
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("Prix de vente"))
    expiration_date = models.DateField(null=True, blank=True, verbose_name=_("Date d'expiration"))
    qr_code_image = models.ImageField(upload_to='qr_codes/', blank=True, null=True, verbose_name=_("QR Code"))

    class Meta:
        verbose_name = _("Produit")
        verbose_name_plural = _("Produits")

    def clean(self):
         # 1) Vérifier qu'une catégorie est bien renseignée
        if self.category_id is None:
            raise ValidationError({
                'category': _("La catégorie est obligatoire.")
            })

        # 2) Ta logique métier existante sur CATEGORY_MAP
        allowed = CATEGORY_MAP.get(self.category.name, [])
        if self.name not in allowed:
            raise ValidationError({
                'name': _(f"Le produit '{self.name}' n'est pas valide pour la catégorie '{self.category.name}'.")
            })

        # 3) Validation de date d'expiration si présente
        if self.expiration_date and self.expiration_date < timezone.now().date():
            raise ValidationError({
                'expiration_date': _("Date d'expiration dépassée.")
            })
    def save(self, *args, **kwargs):
        self.clean()
        # Génération du QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(f"Produit: {self.name} | Prix: {self.selling_price}")
        qr.make(fit=True)
        img = qr.make_image(fill_color='black', back_color='white')
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        file_name = f"qr_{uuid.uuid4().hex}.png"
        self.qr_code_image.save(file_name, File(buffer), save=False)
        super().save(*args, **kwargs)


class Supplier(models.Model):
    TYPE_CHOICES = [
        ('ENGRAIS', 'Engrais'),
        ('SEMENCES', 'Semences'),
        ('OUTILS', 'Outils agricoles'),
    ]
    name = models.CharField(max_length=100, verbose_name=_("Nom"))
    contact = models.CharField(max_length=100, verbose_name=_("Contact"))
    product_type = models.CharField(max_length=20, choices=TYPE_CHOICES, verbose_name=_("Type de produit"))
    address = models.TextField(verbose_name=_("Adresse"))
    date_added = models.DateTimeField(auto_now_add=True, verbose_name=_("Date d'ajout"))

    class Meta:
        verbose_name = _("Fournisseur")
        verbose_name_plural = _("Fournisseurs")

    def __str__(self):
        return f"{self.name} - {self.get_product_type_display()}"


class ClientProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='client_profile')
    location = models.CharField(max_length=100, verbose_name=_("Localisation"))
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name=_("Solde"))

    class Meta:
        verbose_name = _("Client")
        verbose_name_plural = _("Clients")

    def __str__(self):
        return self.user.username


class Order(models.Model):
    client = models.ForeignKey(ClientProfile, on_delete=models.CASCADE, related_name='orders', verbose_name=_("Client"))
    date_ordered = models.DateTimeField(auto_now_add=True, verbose_name=_("Date de commande"))
    status = models.CharField(max_length=20, choices=[
        ('PENDING', 'En attente'),
        ('EN_COURS', 'En cours'),
        ('DELIVERED', 'Livrée'),
        ('CANCELLED', 'Annulée')
    ], default='PENDING', verbose_name=_("Statut"))
    total = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("Total"))

    class Meta:
        verbose_name = _("Commande")
        verbose_name_plural = _("Commandes")

    def __str__(self):
        return f"Commande #{self.id} - {self.client.user.username}"

    def update_status_if_paid(self):
        if sum(p.amount for p in self.payments.filter(status='PAID')) >= self.total:
            self.status = 'EN_COURS'
            self.save()


class OrderLine(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='lines')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(verbose_name=_("Quantité"))
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("Prix unitaire"))

    class Meta:
        verbose_name = _("Ligne de commande")
        verbose_name_plural = _("Lignes de commande")

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"


class StockAlert(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='alerts')
    threshold = models.PositiveIntegerField(verbose_name=_("Seuil"))
    is_active = models.BooleanField(default=True, verbose_name=_("Active"))

    class Meta:
        verbose_name = _("Alerte de stock")
        verbose_name_plural = _("Alertes de stock")

    def check_stock(self):
        if self.is_active and self.product.quantity_in_stock <= self.threshold:
            send_alert(self.product.category, f"Stock faible pour {self.product.name}")
            return True
        return False


class ProductReview(models.Model):
    RATING_CHOICES = [(i, '★'*i + '☆'*(5-i)) for i in range(1,6)]
    client = models.ForeignKey(ClientProfile, on_delete=models.CASCADE, related_name='reviews')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveSmallIntegerField(choices=RATING_CHOICES, verbose_name=_("Note"))
    comment = models.TextField(blank=True, verbose_name=_("Commentaire"))
    created_at = models.DateTimeField(auto_now_add=True)
    verified_purchase = models.BooleanField(default=False)

    class Meta:
        unique_together = ('client', 'product')
        verbose_name = _("Avis produit")
        verbose_name_plural = _("Avis produits")

    def __str__(self):
        return f"{self.rating}/5 - {self.product.name}"


class RefundRequest(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='refunds')
    reason = models.TextField(verbose_name=_("Raison"))
    evidence = models.FileField(
        upload_to='refunds/',
        validators=[FileExtensionValidator(['pdf','jpg','png'])],
        verbose_name=_("Preuve")
    )
    status = models.CharField(max_length=20, choices=[
        ('PENDING','En attente'),('APPROVED','Approuvé'),('REJECTED','Rejeté')
    ], default='PENDING', verbose_name=_("Statut"))
    requested_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _("Demande de remboursement")
        verbose_name_plural = _("Demandes de remboursement")

    @property
    def is_eligible(self):
        return self.order.status == 'DELIVERED' and (timezone.now() - self.order.date_ordered) <= timedelta(days=14)


class LoyaltyProgram(models.Model):
    client = models.OneToOneField(ClientProfile, on_delete=models.CASCADE, related_name='loyalty')
    points = models.PositiveIntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)
    transactions = models.JSONField(default=list)

    class Meta:
        verbose_name = _("Programme fidélité")
        verbose_name_plural = _("Programmes fidélité")

    def add_points(self, order):
        earned = int(order.total // 10)
        self.points += earned
        self.transactions.append({
            'date': timezone.now().isoformat(),
            'order': order.id,
            'points': earned
        })
        self.save()
        return earned


class Payment(models.Model):
    PAYMENT_METHODS = [
        ('CARD','Carte bancaire'),('BANK','Virement'),
        ('MOBILE','Mobile Money'),('PAYPAL','PayPal'),
        ('APPLE_PAY','Apple Pay'),('GOOGLE_PAY','Google Pay')
    ]
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments')
    method = models.CharField(max_length=20, choices=PAYMENT_METHODS, verbose_name=_("Méthode"))
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_("Montant"))
    status = models.CharField(max_length=20, choices=[
        ('PENDING','En attente'),('PAID','Payé'),('FAILED','Échoué')
    ], default='PENDING', verbose_name=_("Statut"))
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _("Paiement")
        verbose_name_plural = _("Paiements")

    def __str__(self):
        return f"Paiement #{self.id} – {self.get_method_display()} – {self.status}"

    def save(self, *args, **kwargs):
        # transaction sûre
        with transaction.atomic():
            super().save(*args, **kwargs)
            if self.status == 'PAID':
                # met à jour la date et la commande
                if not self.paid_at:
                    self.paid_at = timezone.now()
                    super().save(update_fields=['paid_at'])
                self.order.update_status_if_paid()


class Delivery(models.Model):
    class Type(models.TextChoices):
        LIVRAISON = 'LIVRAISON', _('Problème de livraison')
        STOCK = 'STOCK', _('Intervention sur le stock')
        REMBOURSEMENT = 'REMBOURSEMENT', _('Suivi de remboursement')
        AUTRE = 'AUTRE', _('Autre')

    class Status(models.TextChoices):
        EN_ATTENTE = 'EN_ATTENTE', _('En attente')
        EN_COURS = 'EN_COURS', _('En cours')
        TERMINEE = 'TERMINEE', _('Terminée')

    deliverer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, verbose_name=_("Livreur")
    )
    order = models.ForeignKey(
        Order, on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name=_("Commande concernée")
    )
    product = models.ForeignKey(
        Product, on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name=_("Produit concerné")
    )
    type = models.CharField(
        max_length=20, choices=Type.choices,
        verbose_name=_("Type de livraison")
    )
    status = models.CharField(
        max_length=20, choices=Status.choices,
        default=Status.EN_ATTENTE, verbose_name=_("Statut")
    )
    description = models.TextField(verbose_name=_("Description"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Date de création"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Date de mise à jour"))

    class Meta:
        verbose_name = _("Livraison")
        verbose_name_plural = _("Livraisons")
        ordering = ['-created_at']
