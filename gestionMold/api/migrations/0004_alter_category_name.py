# Generated by Django 5.2 on 2025-05-06 11:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0003_alter_category_name'),
    ]

    operations = [
        migrations.AlterField(
            model_name='category',
            name='name',
            field=models.CharField(choices=[('Céréales', 'Céréales'), ('Légumes', 'Légumes'), ('Fruits', 'Fruits'), ('Cultures industrielles', 'Cultures industrielles'), ('Tubercules et racines', 'Tubercules et racines'), ('Légumineuses et oléagineux', 'Légumineuses et oléagineux')], help_text='Choisir une catégorie parmi la liste standard', max_length=50, unique=True, verbose_name='Catégorie'),
        ),
    ]
