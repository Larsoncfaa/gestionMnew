# Generated by Django 4.2.21 on 2025-05-11 02:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0019_alter_category_name'),
    ]

    operations = [
        migrations.AlterField(
            model_name='category',
            name='name',
            field=models.CharField(choices=[('Fruits non tropicaux', 'Fruits non tropicaux'), ('Légumes', 'Légumes'), ('Fruits tropicaux', 'Fruits tropicaux'), ('Légumineuses et oléagineux', 'Légumineuses et oléagineux'), ('Cultures industrielles', 'Cultures industrielles'), ('Produits transformés', 'Produits transformés'), ('Fruits à coque', 'Fruits à coque'), ('Céréales', 'Céréales'), ('Plantes à fibres', 'Plantes à fibres'), ('Tubercules et racines', 'Tubercules et racines'), ('Agrumes', 'Agrumes'), ('Plantes fourragères', 'Plantes fourragères'), ('Graines oléagineuses', 'Graines oléagineuses'), ('Champignons et produits forestiers', 'Champignons et produits forestiers'), ('Plantes aromatiques et médicinales', 'Plantes aromatiques et médicinales'), ('Épices', 'Épices'), ('Plantes sucrières', 'Plantes sucrières'), ('Plantes énergétiques', 'Plantes énergétiques')], help_text='Choisir une catégorie parmi la liste standard', max_length=50, unique=True, verbose_name='Catégorie'),
        ),
    ]
