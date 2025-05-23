# Generated by Django 4.2.21 on 2025-05-22 02:04

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0026_alter_order_total_alter_orderline_unit_price_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='orderline',
            name='unit_price',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, validators=[django.core.validators.MinValueValidator(0)], verbose_name='Prix unitaire'),
        ),
    ]
