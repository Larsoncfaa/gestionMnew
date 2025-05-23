# Generated by Django 5.2 on 2025-05-05 23:26

import django.contrib.auth.models
import django.contrib.auth.validators
import django.core.validators
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(choices=[('Tubercules et racines', 'Tubercules et racines'), ('Légumineuses et oléagineux', 'Légumineuses et oléagineux'), ('Légumes', 'Légumes'), ('Fruits', 'Fruits'), ('Céréales', 'Céréales'), ('Cultures industrielles', 'Cultures industrielles')], help_text='Choisir une catégorie parmi la liste standard', max_length=50, unique=True, verbose_name='Catégorie')),
            ],
            options={
                'verbose_name': 'Catégorie',
                'verbose_name_plural': 'Catégories',
            },
        ),
        migrations.CreateModel(
            name='Supplier',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='Nom')),
                ('contact', models.CharField(max_length=100, verbose_name='Contact')),
                ('product_type', models.CharField(choices=[('ENGRAIS', 'Engrais'), ('SEMENCES', 'Semences'), ('OUTILS', 'Outils agricoles')], max_length=20, verbose_name='Type de produit')),
                ('address', models.TextField(verbose_name='Adresse')),
                ('date_added', models.DateTimeField(auto_now_add=True, verbose_name="Date d'ajout")),
            ],
            options={
                'verbose_name': 'Fournisseur',
                'verbose_name_plural': 'Fournisseurs',
            },
        ),
        migrations.CreateModel(
            name='CustomUser',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('username', models.CharField(error_messages={'unique': 'A user with that username already exists.'}, help_text='Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.', max_length=150, unique=True, validators=[django.contrib.auth.validators.UnicodeUsernameValidator()], verbose_name='username')),
                ('first_name', models.CharField(blank=True, max_length=150, verbose_name='first name')),
                ('last_name', models.CharField(blank=True, max_length=150, verbose_name='last name')),
                ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', verbose_name='active')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('email', models.EmailField(max_length=254, unique=True)),
                ('phone', models.CharField(blank=True, max_length=20, null=True)),
                ('language', models.CharField(default='fr', max_length=5)),
                ('is_verified', models.BooleanField(default=False)),
                ('is_agriculteur', models.BooleanField(default=False)),
                ('is_livreur', models.BooleanField(default=False)),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.group', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.permission', verbose_name='user permissions')),
            ],
            options={
                'verbose_name': 'Utilisateur',
                'verbose_name_plural': 'Utilisateurs',
            },
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name='ClientProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('location', models.CharField(max_length=100, verbose_name='Localisation')),
                ('balance', models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='Solde')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='client_profile', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Client',
                'verbose_name_plural': 'Clients',
            },
        ),
        migrations.CreateModel(
            name='LoyaltyProgram',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('points', models.PositiveIntegerField(default=0)),
                ('last_updated', models.DateTimeField(auto_now=True)),
                ('transactions', models.JSONField(default=list)),
                ('client', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='loyalty', to='api.clientprofile')),
            ],
            options={
                'verbose_name': 'Programme fidélité',
                'verbose_name_plural': 'Programmes fidélité',
            },
        ),
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_ordered', models.DateTimeField(auto_now_add=True, verbose_name='Date de commande')),
                ('status', models.CharField(choices=[('PENDING', 'En attente'), ('EN_COURS', 'En cours'), ('DELIVERED', 'Livrée'), ('CANCELLED', 'Annulée')], default='PENDING', max_length=20, verbose_name='Statut')),
                ('total', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Total')),
                ('client', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='orders', to='api.clientprofile', verbose_name='Client')),
            ],
            options={
                'verbose_name': 'Commande',
                'verbose_name_plural': 'Commandes',
            },
        ),
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('method', models.CharField(choices=[('CARD', 'Carte bancaire'), ('BANK', 'Virement'), ('MOBILE', 'Mobile Money'), ('PAYPAL', 'PayPal'), ('APPLE_PAY', 'Apple Pay'), ('GOOGLE_PAY', 'Google Pay')], max_length=20, verbose_name='Méthode')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Montant')),
                ('status', models.CharField(choices=[('PENDING', 'En attente'), ('PAID', 'Payé'), ('FAILED', 'Échoué')], default='PENDING', max_length=20, verbose_name='Statut')),
                ('paid_at', models.DateTimeField(blank=True, null=True)),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payments', to='api.order')),
            ],
            options={
                'verbose_name': 'Paiement',
                'verbose_name_plural': 'Paiements',
            },
        ),
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='Nom')),
                ('description', models.TextField(blank=True, null=True, verbose_name='Description')),
                ('image', models.ImageField(blank=True, null=True, upload_to='products/', verbose_name='Image')),
                ('quantity_in_stock', models.PositiveIntegerField(default=0, verbose_name='Quantité en stock')),
                ('unit', models.CharField(choices=[('kg', 'Kilogramme'), ('g', 'Gramme'), ('l', 'Litre')], max_length=5, verbose_name='Unité')),
                ('purchase_price', models.DecimalField(decimal_places=2, max_digits=10, verbose_name="Prix d'achat")),
                ('selling_price', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Prix de vente')),
                ('expiration_date', models.DateField(blank=True, null=True, verbose_name="Date d'expiration")),
                ('qr_code_image', models.ImageField(blank=True, null=True, upload_to='qr_codes/', verbose_name='QR Code')),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='api.category', verbose_name='Catégorie')),
            ],
            options={
                'verbose_name': 'Produit',
                'verbose_name_plural': 'Produits',
            },
        ),
        migrations.CreateModel(
            name='OrderLine',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.PositiveIntegerField(verbose_name='Quantité')),
                ('unit_price', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Prix unitaire')),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lines', to='api.order')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='api.product')),
            ],
            options={
                'verbose_name': 'Ligne de commande',
                'verbose_name_plural': 'Lignes de commande',
            },
        ),
        migrations.CreateModel(
            name='Delivery',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.CharField(choices=[('LIVRAISON', 'Problème de livraison'), ('STOCK', 'Intervention sur le stock'), ('REMBOURSEMENT', 'Suivi de remboursement'), ('AUTRE', 'Autre')], max_length=20, verbose_name='Type de livraison')),
                ('status', models.CharField(choices=[('EN_ATTENTE', 'En attente'), ('EN_COURS', 'En cours'), ('TERMINEE', 'Terminée')], default='EN_ATTENTE', max_length=20, verbose_name='Statut')),
                ('description', models.TextField(verbose_name='Description')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Date de création')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Date de mise à jour')),
                ('deliverer', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='Livreur')),
                ('order', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='api.order', verbose_name='Commande concernée')),
                ('product', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='api.product', verbose_name='Produit concerné')),
            ],
            options={
                'verbose_name': 'Livraison',
                'verbose_name_plural': 'Livraisons',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='RefundRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reason', models.TextField(verbose_name='Raison')),
                ('evidence', models.FileField(upload_to='refunds/', validators=[django.core.validators.FileExtensionValidator(['pdf', 'jpg', 'png'])], verbose_name='Preuve')),
                ('status', models.CharField(choices=[('PENDING', 'En attente'), ('APPROVED', 'Approuvé'), ('REJECTED', 'Rejeté')], default='PENDING', max_length=20, verbose_name='Statut')),
                ('requested_at', models.DateTimeField(auto_now_add=True)),
                ('processed_at', models.DateTimeField(blank=True, null=True)),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='refunds', to='api.order')),
            ],
            options={
                'verbose_name': 'Demande de remboursement',
                'verbose_name_plural': 'Demandes de remboursement',
            },
        ),
        migrations.CreateModel(
            name='StockAlert',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('threshold', models.PositiveIntegerField(verbose_name='Seuil')),
                ('is_active', models.BooleanField(default=True, verbose_name='Active')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='alerts', to='api.product')),
            ],
            options={
                'verbose_name': 'Alerte de stock',
                'verbose_name_plural': 'Alertes de stock',
            },
        ),
        migrations.CreateModel(
            name='ProductReview',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rating', models.PositiveSmallIntegerField(choices=[(1, '★☆☆☆☆'), (2, '★★☆☆☆'), (3, '★★★☆☆'), (4, '★★★★☆'), (5, '★★★★★')], verbose_name='Note')),
                ('comment', models.TextField(blank=True, verbose_name='Commentaire')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('verified_purchase', models.BooleanField(default=False)),
                ('client', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reviews', to='api.clientprofile')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reviews', to='api.product')),
            ],
            options={
                'verbose_name': 'Avis produit',
                'verbose_name_plural': 'Avis produits',
                'unique_together': {('client', 'product')},
            },
        ),
    ]
