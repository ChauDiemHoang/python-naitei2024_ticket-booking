# Generated by Django 3.2.25 on 2024-08-22 08:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0004_flight_airline'),
    ]

    operations = [
        migrations.AlterField(
            model_name='passenger',
            name='passport_number',
            field=models.CharField(default='N12345678', max_length=255),
        ),
    ]
