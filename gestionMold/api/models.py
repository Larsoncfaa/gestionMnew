import uuid
from io import BytesIO
from datetime import timedelta

# Django imports
from django.conf import settings
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.core.exceptions import ValidationError
from django.core.files import File
from django.core.validators import FileExtensionValidator, MinValueValidator
from django.db import models, transaction
from django.db.models import F, Sum, Index
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
import qrcode

# Local imports
from .constants import UNIT_CHOICES
from .utils import send_alert, generate_pdf  # suppose generate_pdf exists


# ---------- Utilisateur personnalisé avec audit ----------

class CustomUser(AbstractUser):
    """
    Extension de AbstractUser pour gérer rôles, permissions et audit.
    """
    email = models.EmailField(
        unique=True,
        verbose_name=_("Email")
    )
    phone = models.CharField(
        max_length=20,
        blank=True, null=True,
        verbose_name=_("Téléphone")
    )
    language = models.CharField(
        max_length=5,
        default='fr',
        verbose_name=_("Langue")
    )
    is_verified = models.BooleanField(
        default=False,
        verbose_name=_("Vérifié")
    )
    is_agriculteur = models.BooleanField(
        default=False,
        verbose_name=_("Agriculteur")
    )
    is_livreur = models.BooleanField(
        default=False,
        verbose_name=_("Livreur")
    )
    is_client = models.BooleanField(
        default=False,
        verbose_name=_("Client")
    )

    REQUIRED_FIELDS = ['email', 'first_name', 'last_name']

    class Meta:
        verbose_name = _("Utilisateur")
        verbose_name_plural = _("Utilisateurs")
        indexes = [
            Index(fields=['email']),
            Index(fields=['username']),
        ]

    def save(self, *args, **kwargs):
        self.email = self.email.lower().strip()
        
        # Vérifie qu’un autre utilisateur n’a pas déjà cet email
        if not self.pk and CustomUser.objects.filter(email=self.email).exists():
            raise ValidationError({'email': _("Cet email est déjà utilisé.")})
        
        # Génération d’un username unique si vide
        if not self.username:
            base = f"{self.first_name[0] if self.first_name else 'u'}{self.last_name}".lower()
            base = base or self.email.split('@')[0]
            unique_suffix = uuid.uuid4().hex[:4]
            self.username = f"{base}-{unique_suffix}"
        
        super().save(*args, **kwargs)

    def __str__(self):
        return self.get_full_name() or self.username


# ---------- Catégories & Produits ----------

class Category(models.Model):
    """
    Catégories libres saisies par l’utilisateur.
    """
    name = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_("Catégorie"),
        help_text=_("Saisir ou choisir une catégorie existante")
    )

    class Meta:
        verbose_name = _("Catégorie")
        verbose_name_plural = _("Catégories")
        indexes = [Index(fields=['name'])]

    def __str__(self):
        return self.name


class Product(models.Model):
    """
    Produit avec gestion de stock, image, QR code.
    """
    name = models.CharField(
        max_length=100,
        verbose_name=_("Nom")
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="produits",
        verbose_name=_("Catégorie")
    )
    description = models.TextField(
        blank=True, null=True,
        verbose_name=_("Description")
    )
    image = models.ImageField(
        upload_to='products/',
        blank=True, null=True,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png'])],
        verbose_name=_("Image")
    )
    quantity_in_stock = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Quantité en stock")
    )
    unit = models.CharField(
        max_length=5,
        choices=UNIT_CHOICES,
        verbose_name=_("Unité")
    )
    purchase_price = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name=_("Prix d'achat")
    )
    selling_price = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name=_("Prix de vente")
    )
    expiration_date = models.DateField(
        blank=True, null=True,
        verbose_name=_("Date d'expiration")
    )
    qr_code_image = models.ImageField(
        upload_to='qr_codes/',
        blank=True, null=True,
        verbose_name=_("QR Code")
    )

    class Meta:
        verbose_name = _("Produit")
        verbose_name_plural = _("Produits")
        unique_together = ('name', 'category')
        indexes = [
            Index(fields=['name']),
            Index(fields=['category']),
        ]

    def clean(self):
        if not self.name:
            raise ValidationError({'name': _("Le nom du produit est obligatoire.")})
        if not self.category:
            raise ValidationError({'category': _("La catégorie est obligatoire.")})
        if self.expiration_date and self.expiration_date < timezone.now().date():
            raise ValidationError({'expiration_date': _("Date d'expiration dépassée.")})

    def save(self, *args, **kwargs):
        self.clean()
        regenerate = not self.pk or not self.qr_code_image
        if not regenerate:
            old = Product.objects.filter(pk=self.pk).values('name', 'selling_price').first()
            if old and (old['name'] != self.name or old['selling_price'] != self.selling_price):
                regenerate = True
        if regenerate:
            qr = qrcode.QRCode(version=1, box_size=10, border=4)
            qr.add_data(f"Produit: {self.name} | Prix: {self.selling_price}")
            qr.make(fit=True)
            img = qr.make_image(fill_color='black', back_color='white')
            buf = BytesIO()
            img.save(buf, format='PNG')
            self.qr_code_image.save(f"qr_{uuid.uuid4().hex}.png", File(buf), save=False)
        super().save(*args, **kwargs)

        
    def delete(self, *args, **kwargs):
        if self.image:
            self.image.delete(save=False)
        super().delete(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.category.name})"


# ---------- Fournisseurs & Approvisionnement ----------

class Supplier(models.Model):
    """
    Fournisseur de semences, engrais ou outils.
    """
    ENGRAIS = 'ENGRAIS'
    SEMENCES = 'SEMENCES'
    OUTILS = 'OUTILS'
    TYPE_CHOICES = [
        (ENGRAIS, _('Engrais')),
        (SEMENCES, _('Semences')),
        (OUTILS, _('Outils agricoles')),
    ]

    name = models.CharField(
        max_length=100,
        verbose_name=_("Nom")
    )
    contact = models.CharField(
        max_length=100,
        verbose_name=_("Contact")
    )
    product_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        verbose_name=_("Type")
    )
    address = models.TextField(
        verbose_name=_("Adresse")
    )
    date_added = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Date d'ajout")
    )

    class Meta:
        verbose_name = _("Fournisseur")
        verbose_name_plural = _("Fournisseurs")
        indexes = [
            Index(fields=['name']),
            Index(fields=['product_type']),
        ]

    def __str__(self):
        return f"{self.name} – {self.get_product_type_display()}"


# ---------- Entrepôts, Lots & Mouvements de stock ----------

class Warehouse(models.Model):
    """
    Entrepôt physique.
    """
    name = models.CharField(
        max_length=100,
        verbose_name=_("Nom")
    )
    location = models.CharField(
        max_length=200,
        verbose_name=_("Localisation")
    )

    class Meta:
        verbose_name = _("Entrepôt")
        verbose_name_plural = _("Entrepôts")

    def __str__(self):
        return self.name


class Batch(models.Model):
    """
    Lot de production ou numéro de série.
    """
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="lots",
        verbose_name=_("Produit")
    )
    lot_number = models.CharField(
        max_length=50,
        verbose_name=_("Numéro de lot")
    )
    expiration_date = models.DateField(
        blank=True, null=True,
        verbose_name=_("Date d'expiration")
    )

    class Meta:
        verbose_name = _("Lot")
        verbose_name_plural = _("Lots")

    def __str__(self):
        return f"{self.product.name} – Lot {self.lot_number}"


class StockLevel(models.Model):
    """
    Niveau de stock par entrepôt.
    """
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="niveaux_stock",
        verbose_name=_("Produit")
    )
    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name="niveaux_stock",
        verbose_name=_("Entrepôt")
    )
    quantity = models.PositiveIntegerField(
        verbose_name=_("Quantité")
    )

    class Meta:
        verbose_name = _("Niveau de stock")
        verbose_name_plural = _("Niveaux de stock")
        unique_together = ('product', 'warehouse')

    def __str__(self):
        return f"{self.product.name} @ {self.warehouse.name}: {self.quantity}"


class StockMovement(models.Model):
    """
    Représente un mouvement de stock : entrée, sortie ou ajustement.
    """
    IN = 'IN'
    OUT = 'OUT'
    ADJ = 'ADJ'

    MOVEMENT_CHOICES = [
        (IN, _('Entrée')),
        (OUT, _('Sortie')),
        (ADJ, _('Ajustement')),
    ]

    product = models.ForeignKey(
        'Product',
        on_delete=models.CASCADE,
        related_name="mouvements_stock",
        verbose_name=_("Produit")
    )
    warehouse = models.ForeignKey(
        'Warehouse',
        on_delete=models.CASCADE,
        related_name="mouvements_stock",
        verbose_name=_("Entrepôt")
    )
    batch = models.ForeignKey(
        'Batch',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="mouvements_stock",
        verbose_name=_("Lot")
    )
    movement_type = models.CharField(
        max_length=3,
        choices=MOVEMENT_CHOICES,
        verbose_name=_("Type de mouvement")
    )
    quantity = models.PositiveIntegerField(
        verbose_name=_("Quantité")
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Date et heure")
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name=_("Utilisateur")
    )

    class Meta:
        verbose_name = _("Mouvement de stock")
        verbose_name_plural = _("Mouvements de stock")
        ordering = ['-timestamp']

    def save(self, *args, **kwargs):
        # Enregistrement du mouvement
        is_new = self.pk is None
        super().save(*args, **kwargs)

        if is_new:
            # Mise à jour ou création du niveau de stock
            niveau, created = StockLevel.objects.get_or_create(
                product=self.product,
                warehouse=self.warehouse,
                defaults={'quantity': 0}
            )

            # Ajustement en fonction du type
            ajustement = self.quantity
            if self.movement_type == self.OUT:
                ajustement = -self.quantity
            elif self.movement_type == self.ADJ:
                ajustement = self.quantity  # tu peux le rendre plus explicite selon les besoins

            niveau.quantity = F('quantity') + ajustement
            niveau.save()
            niveau.refresh_from_db()

    def __str__(self):
        return f"{self.get_movement_type_display()} - {self.product} ({self.quantity})"

# ---------- Profils clients, Commandes, Factures & Retours ----------

class ClientProfile(models.Model):
    """
    Informations complémentaires pour le client.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profil_client",
        verbose_name=_("Utilisateur")
    )
    location = models.CharField(
        max_length=100,
        verbose_name=_("Localisation")
    )
    balance = models.DecimalField(
        max_digits=10, decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name=_("Solde")
    )

    class Meta:
        verbose_name = _("Profil client")
        verbose_name_plural = _("Profils clients")

    def __str__(self):
        return self.user.username


class Order(models.Model):
    """
    Commande passée par un client.
    """
    PENDING = 'PENDING'
    EN_COURS = 'EN_COURS'
    DELIVERED = 'DELIVERED'
    CANCELLED = 'CANCELLED'
    STATUS_CHOICES = [
        (PENDING, _('En attente')),
        (EN_COURS, _('En cours')),
        (DELIVERED, _('Livrée')),
        (CANCELLED, _('Annulée')),
    ]

    client = models.ForeignKey(
        ClientProfile,
        on_delete=models.CASCADE,
        related_name="commandes",
        verbose_name=_("Client")
    )
    date_ordered = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Date")
    )
    order_status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=PENDING,
        verbose_name=_("Statut commande")
    )
    total = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name=_("Total"),
        default=0,
    )

    class Meta:
        verbose_name = _("Commande")
        verbose_name_plural = _("Commandes")

    def update_total(self):
        total = sum(line.unit_price * line.quantity for line in self.lignes_commandes.all())
        self.total = total
        self.save(update_fields=['total'])

    def update_status_if_paid(self):
        paid = self.payments.filter(payment_status='PAID').aggregate(sum=Sum('amount'))['sum'] or 0
        if paid >= self.total and self.order_status != self.EN_COURS:
            self.order_status = self.EN_COURS
            self.save(update_fields=['order_status'])

    def clean(self):
        if not self.lignes_commandes.exists():
            raise ValidationError("Une commande doit contenir au moins une ligne de commande.")

    def save(self, *args, **kwargs):
        self.full_clean()  # Appelle clean() avant de sauvegarder
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Commande #{self.id} – {self.client.user.username}"


class OrderLine(models.Model):
    """
    Ligne de détail pour chaque commande.
    """
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="lignes_commandes",
        verbose_name=_("Commande")
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="lignes_commandes",
        verbose_name=_("Produit")
    )
    quantity = models.PositiveIntegerField(
        verbose_name=_("Quantité")
    )
    unit_price = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name=_("Prix unitaire"),
        null=True, blank=True


    )

    class Meta:
        verbose_name = _("Ligne de commande")
        verbose_name_plural = _("Lignes de commande")
    
    def save(self, *args, **kwargs):
        # Calcule automatiquement le prix unitaire à partir du produit
        self.unit_price = self.product.selling_price
        super().save(*args, **kwargs)
        # Met à jour le total de la commande après chaque modification de ligne
        self.order.update_total()


    def __str__(self):
        return f"{self.quantity} × {self.product.name}"


class Invoice(models.Model):
    """
    Facture PDF générée pour chaque commande.
    """
    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name="facture",
        verbose_name=_("Commande")
    )
    pdf = models.FileField(
        upload_to='invoices/',
        verbose_name=_("Fichier PDF")
    )
    issued_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Émise le")
    )

    class Meta:
        verbose_name = _("Facture")
        verbose_name_plural = _("Factures")

    def generate_pdf(self):
        self.pdf = generate_pdf(self.order)
        self.save(update_fields=['pdf'])

    def delete(self, *args, **kwargs):
        if self.pdf:
            self.pdf.delete(save=False)
        super().delete(*args, **kwargs)


class ReturnRequest(models.Model):
    """
    Demande de retour physique et remise en stock.
    """
    order_line = models.ForeignKey(
        OrderLine,
        on_delete=models.CASCADE,
        related_name="demandes_retour",
        verbose_name=_("Ligne de commande")
    )
    reason = models.TextField(
        verbose_name=_("Motif")
    )
    quantity = models.PositiveIntegerField(
        verbose_name=_("Quantité")
    )
    approved = models.BooleanField(
        default=False,
        verbose_name=_("Approuvé")
    )
    requested_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Demandé le")
    )
    processed_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name=_("Traité le")
    )

    class Meta:
        verbose_name = _("Demande de retour")
        verbose_name_plural = _("Demandes de retour")


class ExchangeRequest(models.Model):
    """
    Échange de produit suite à un retour.
    """
    return_request = models.OneToOneField(
        ReturnRequest,
        on_delete=models.CASCADE,
        related_name="echange",
        verbose_name=_("Demande de retour")
    )
    replacement = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="echanges",
        verbose_name=_("Produit de remplacement")
    )
    exchange_status = models.CharField(
        max_length=20,
        choices=[('PENDING', _('En attente')), ('COMPLETED', _('Terminé'))],
        default='PENDING',
        verbose_name=_("Statut échange")
    )

    class Meta:
        verbose_name = _("Demande d'échange")
        verbose_name_plural = _("Demandes d'échange")


# ---------- Notifications & Audit ----------

class Notification(models.Model):
    """
    Notification interne (email/SMS ou WebSocket).
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name=_("Utilisateur")
    )
    message = models.TextField(
        verbose_name=_("Message")
    )
    link = models.URLField(
        blank=True, null=True,
        verbose_name=_("Lien")
    )
    read = models.BooleanField(
        default=False,
        verbose_name=_("Lu")
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Créée le")
    )

    class Meta:
        verbose_name = _("Notification")
        verbose_name_plural = _("Notifications")

    def __str__(self):
        return f"Notif #{self.id} – {'Lu' if self.read else 'Non lu'}"


# ---------- Promotions & Remises ----------

class PromoCode(models.Model):
    """
    Codes promo utilisables sur commandes.
    """
    code = models.CharField(
        max_length=20,
        unique=True,
        verbose_name=_("Code")
    )
    discount_percent = models.DecimalField(
        max_digits=5, decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name=_("% de remise")
    )
    valid_from = models.DateTimeField(
        verbose_name=_("Valide à partir de")
    )
    valid_to = models.DateTimeField(
        verbose_name=_("Valide jusqu'à")
    )
    usage_limit = models.PositiveIntegerField(
        null=True, blank=True,
        verbose_name=_("Limite d'utilisation")
    )

    class Meta:
        verbose_name = _("Code promo")
        verbose_name_plural = _("Codes promo")

    def __str__(self):
        return self.code


class ProductDiscount(models.Model):
    """
    Remise spécifique sur un produit.
    """
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="remises",
        verbose_name=_("Produit")
    )
    discount_percent = models.DecimalField(
        max_digits=5, decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name=_("% de remise")
    )

    class Meta:
        verbose_name = _("Remise produit")
        verbose_name_plural = _("Remises produit")

    def __str__(self):
        return f"{self.discount_percent}% sur {self.product.name}"


# ---------- Paiements & Journaux ----------

class PaymentLog(models.Model):
    """
    Historique détaillé des tentatives de paiement.
    """
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="payment_logs",
        verbose_name=_("Commande")
    )
    attempt_time = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Tentative le")
    )
    payment_status = models.CharField(
        max_length=20,
        verbose_name=_("Statut paiement")
    )
    amount = models.DecimalField(
        max_digits=10, decimal_places=2,
        verbose_name=_("Montant")
    )
    info = models.JSONField(
        default=dict, blank=True,
        verbose_name=_("Info")
    )

    class Meta:
        verbose_name = _("Journal de paiement")
        verbose_name_plural = _("Journaux de paiement")

    def __str__(self):
        return f"Log #{self.id} – {self.payment_status}"


class Payment(models.Model):
    """
    Paiement associé à une commande.
    """
    PAYMENT_METHODS = [
        ('CARD', _('Carte bancaire')),
        ('BANK', _('Virement')),
        ('MOBILE', _('Mobile Money')),
        ('PAYPAL', _('PayPal')),
        ('APPLE_PAY', _('Apple Pay')),
        ('GOOGLE_PAY', _('Google Pay')),
        ('BALANCE', _('Solde client')),
    ]
    PENDING = 'PENDING'
    PAID = 'PAID'
    FAILED = 'FAILED'
    STATUS_CHOICES = [
        (PENDING, _('En attente')),
        (PAID, _('Payé')),
        (FAILED, _('Échoué')),
    ]

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="payments",
        verbose_name=_("Commande")
    )
    method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHODS,
        verbose_name=_("Moyen de paiement")
    )
    amount = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name=_("Montant")
    )
    payment_status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=PENDING,
        verbose_name=_("Statut paiement")
    )
    paid_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name=_("Payé le")
    )

    class Meta:
        verbose_name = _("Paiement")
        verbose_name_plural = _("Paiements")
    
    def clean(self):
        # Total déjà payé pour cette commande (hors ce paiement s'il existe déjà)
        total_paid = self.order.payments.exclude(pk=self.pk).filter(payment_status=self.PAID).aggregate(sum=Sum('amount'))['sum'] or 0
        reste = self.order.total - total_paid
        if self.amount > reste:
            raise ValidationError("Le montant du paiement dépasse le total dû pour cette commande.")

    def save(self, *args, **kwargs):
        self.full_clean()  # Appelle clean() avant de sauvegarder
        # Enregistrement du paiement
        with transaction.atomic():
            is_new = self.pk is None
            super().save(*args, **kwargs)
            PaymentLog.objects.create(
                order=self.order,
                payment_status=self.payment_status,
                amount=self.amount,
                info={'new': is_new}
            )
            if self.payment_status == self.PAID and not self.paid_at:
                self.paid_at = timezone.now()
                super().save(update_fields=['paid_at'])
                self.order.update_status_if_paid()

    def __str__(self):
        return f"Paiement #{self.id} – {self.get_payment_status_display()}"


# ---------- Livraisons & Suivi ----------

class Delivery(models.Model):
    """
    Suivi des livraisons et interventions.
    """
    class Type(models.TextChoices):
        LIVRAISON = 'LIVRAISON', _('Problème de livraison')
        STOCK = 'STOCK', _('Intervention stock')
        REMBOURSEMENT = 'REMBOURSEMENT', _('Suivi remboursement')
        AUTRE = 'AUTRE', _('Autre')

    class Status(models.TextChoices):
        EN_ATTENTE = 'EN_ATTENTE', _('En attente')
        EN_COURS = 'EN_COURS', _('En cours')
        TERMINEE = 'TERMINEE', _('Terminée')

    deliverer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="deliveries",
        verbose_name=_("Livreur")
    )
    order = models.ForeignKey(
        Order,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="deliveries",
        verbose_name=_("Commande")
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="deliveries",
        verbose_name=_("Produit")
    )
    type = models.CharField(
        max_length=20,
        choices=Type.choices,
        verbose_name=_("Type")
    )
    delivery_status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.EN_ATTENTE,
        verbose_name=_("Statut livraison")
    )
    description = models.TextField(
        verbose_name=_("Description")
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Créée le")
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Mis à jour le")
    )

    class Meta:
        verbose_name = _("Livraison")
        verbose_name_plural = _("Livraisons")

    def __str__(self):
        return f"{self.get_type_display()} – {self.get_delivery_status_display()}"


class TrackingInfo(models.Model):
    """
    Historique GPS/statut de chaque livraison.
    """
    delivery = models.ForeignKey(
        Delivery,
        on_delete=models.CASCADE,
        related_name="tracking_infos",
        verbose_name=_("Livraison")
    )
    tracking_status = models.CharField(
        max_length=50,
        verbose_name=_("Statut des suivis")
    )
    location = models.CharField(
        max_length=200,
        verbose_name=_("Localisation")
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Horodatage")
    )

    class Meta:
        verbose_name = _("Info de suivi")
        verbose_name_plural = _("Infos de suivi")

    def __str__(self):
        return f"{self.tracking_status} @ {self.location}"


class Proof(models.Model):
    """
    Preuve de livraison (photo, signature).
    """
    delivery = models.ForeignKey(
        Delivery,
        on_delete=models.CASCADE,
        related_name="proofs",
        verbose_name=_("Livraison")
    )
    image = models.ImageField(
        upload_to='delivery_proofs/',
        verbose_name=_("Image")
    )
    uploaded_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Uploadé le")
    )

    class Meta:
        verbose_name = _("Preuve de livraison")
        verbose_name_plural = _("Preuves de livraison")

    def delete(self, *args, **kwargs):
        if self.image:
            self.image.delete(save=False)
        super().delete(*args, **kwargs)
        # Suppression de l'image du système de fichiers
    
       

    def __str__(self):
        return f"Preuve #{self.id}"


# ---------- Alertes, Avis, Remboursements & Fidélité ----------

class StockAlert(models.Model):
    """
    Alerte de stock faible.
    """
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="alerts",
        verbose_name=_("Produit")
    )
    threshold = models.PositiveIntegerField(
        verbose_name=_("Seuil")
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Active")
    )

    class Meta:
        verbose_name = _("Alerte de stock")
        verbose_name_plural = _("Alertes de stock")

    def check_stock(self):
        if self.product.quantity_in_stock <= self.threshold:
            message = _(
                f"Stock faible pour {self.product.name}: "
                f"{self.product.quantity_in_stock} unités restantes."
            )
            send_alert(self.product.category, message)
            Notification.objects.create(
                user=self.product.category.user,
                message=message,
                link=f"/products/{self.product.id}/",
                read=False
            )

    def __str__(self):
        return f"Alerte {self.product.name} ≤ {self.threshold}"


class ProductReview(models.Model):
    """
    Avis laissé par un client sur un produit.
    """
    RATING_CHOICES = [(i, '★'*i + '☆'*(5-i)) for i in range(1,6)]

    client = models.ForeignKey(
        ClientProfile,
        on_delete=models.CASCADE,
        related_name="reviews",
        verbose_name=_("Client")
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="reviews",
        verbose_name=_("Produit")
    )
    rating = models.PositiveSmallIntegerField(
        choices=RATING_CHOICES,
        verbose_name=_("Note")
    )
    comment = models.TextField(
        blank=True,
        verbose_name=_("Commentaire")
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Créé le")
    )
    verified_purchase = models.BooleanField(
        default=False,
        verbose_name=_("Achat vérifié")
    )

    class Meta:
        verbose_name = _("Avis produit")
        verbose_name_plural = _("Avis produits")
        unique_together = ('client', 'product')

    def __str__(self):
        return f"{self.rating}/5 – {self.product.name}"


class RefundRequest(models.Model):
    """
    Demande de remboursement.
    """
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="refunds",
        verbose_name=_("Commande")
    )
    reason = models.TextField(
        verbose_name=_("Motif")
    )
    evidence = models.FileField(
        upload_to='refunds/',
        validators=[FileExtensionValidator(['pdf','jpg','png'])],
        verbose_name=_("Pièce justificative")
    )
    refund_status = models.CharField(
        max_length=20,
        choices=[
            ('PENDING', _('En attente')),
            ('APPROVED', _('Approuvé')),
            ('REJECTED', _('Rejeté'))
        ],
        default='PENDING',
        verbose_name=_("Statut remboursement")
    )
    requested_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Demandé le")
    )
    processed_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name=_("Traité le")
    )

    class Meta:
        verbose_name = _("Demande de remboursement")
        verbose_name_plural = _("Demandes de remboursement")

    @property
    def is_eligible(self):
        return (
            self.order.status == Order.DELIVERED and
            (timezone.now() - self.order.date_ordered) <= timedelta(days=14)
        )
    def delete(self, *args, **kwargs):
        if self.evidence:
            self.evidence.delete(save=False)
        super().delete(*args, **kwargs)
        # Delete the associated evidence file if it exists
        
    def __str__(self):
        return f"Remb #{self.id} – {self.get_status_display()}"


class LoyaltyProgram(models.Model):
    """
    Programme de fidélité client.
    """
    client = models.OneToOneField(
        ClientProfile,
        on_delete=models.CASCADE,
        related_name="loyalty",
        verbose_name=_("Client")
    )
    points = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Points")
    )
    last_updated = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Mis à jour le")
    )
    transactions = models.JSONField(
        default=list, blank=True,
        verbose_name=_("Transactions")
    )

    class Meta:
        verbose_name = _("Programme de fidélité")
        verbose_name_plural = _("Programmes de fidélité")

    def add_points(self, order):
        earned = int(order.total // 10)
        LoyaltyProgram.objects.filter(pk=self.pk).update(points=F('points') + earned)
        self.refresh_from_db()
        self.transactions.append({
            'date': timezone.now().isoformat(),
            'order': order.id,
            'points': earned
        })
        self.save(update_fields=['transactions'])
        return earned

    def __str__(self):
        return f"{self.client.user.username} – {self.points} pts"

    
    def use_points(self, points, reason="Utilisation", order=None):
        if self.points < points:
            raise ValidationError("Pas assez de points.")
        LoyaltyProgram.objects.filter(pk=self.pk).update(points=F('points') - points)
        self.refresh_from_db()
        self.transactions.append({
        'date': timezone.now().isoformat(),
        'order': order.id if order else None,
        'points': -points,
        'reason': reason
    })
        self.save(update_fields=['transactions'])
        return points