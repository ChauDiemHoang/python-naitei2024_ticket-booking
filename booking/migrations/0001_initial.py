# Generated by Django 3.2.25 on 2024-08-14 02:55

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Account',
            fields=[
                ('account_id', models.AutoField(primary_key=True, serialize=False)),
                ('email', models.EmailField(max_length=254, unique=True)),
                ('phone_number', models.CharField(max_length=20)),
                ('password_hash', models.CharField(max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('status', models.CharField(choices=[('Active', 'Active'), ('Suspended', 'Suspended')], default='Active', max_length=10)),
                ('role', models.CharField(choices=[('Admin', 'Admin'), ('Member', 'Member')], default='Member', max_length=10)),
            ],
        ),
        migrations.CreateModel(
            name='Airport',
            fields=[
                ('airport_code', models.CharField(max_length=10, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('city', models.CharField(max_length=255)),
                ('country', models.CharField(max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='Booking',
            fields=[
                ('booking_id', models.AutoField(primary_key=True, serialize=False)),
                ('booking_date', models.DateTimeField(auto_now_add=True)),
                ('seat_number', models.CharField(max_length=10)),
                ('status', models.CharField(choices=[('Confirmed', 'Confirmed'), ('Canceled', 'Canceled')], default='Confirmed', max_length=10)),
                ('account', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='booking.account')),
            ],
        ),
        migrations.CreateModel(
            name='Card',
            fields=[
                ('card_id', models.AutoField(primary_key=True, serialize=False)),
                ('card_number', models.CharField(max_length=16)),
                ('cardholder_name', models.CharField(max_length=255)),
                ('expiry_date', models.DateField()),
                ('card_type', models.CharField(choices=[('Visa', 'Visa'), ('MasterCard', 'MasterCard')], max_length=10)),
                ('billing_address', models.CharField(max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='Flight',
            fields=[
                ('flight_id', models.AutoField(primary_key=True, serialize=False)),
                ('flight_number', models.CharField(max_length=255)),
                ('departure_time', models.DateTimeField()),
                ('arrival_time', models.DateTimeField()),
                ('base_price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('arrival_airport', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='arrivals', to='booking.airport')),
                ('departure_airport', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='departures', to='booking.airport')),
            ],
        ),
        migrations.CreateModel(
            name='TicketType',
            fields=[
                ('ticket_type_id', models.AutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('multiplier', models.DecimalField(decimal_places=2, max_digits=5)),
                ('seat_percentage', models.DecimalField(decimal_places=2, max_digits=5)),
            ],
        ),
        migrations.CreateModel(
            name='User',
            fields=[
                ('user_id', models.AutoField(primary_key=True, serialize=False)),
                ('first_name', models.CharField(max_length=255, verbose_name='first name')),
                ('last_name', models.CharField(max_length=255, verbose_name='last name')),
                ('gender', models.CharField(blank=True, choices=[('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')], max_length=255, null=True, verbose_name='gender')),
                ('nationality', models.CharField(max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='Voucher',
            fields=[
                ('voucher_id', models.AutoField(primary_key=True, serialize=False)),
                ('code', models.CharField(max_length=255)),
                ('quantity', models.IntegerField()),
                ('description', models.CharField(max_length=255)),
                ('discount_amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('discount_percentage', models.IntegerField()),
                ('expiry_date', models.DateField()),
            ],
        ),
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('payment_id', models.AutoField(primary_key=True, serialize=False)),
                ('payment_date', models.DateTimeField(auto_now_add=True)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('payment_method', models.CharField(choices=[('Credit Card', 'Credit Card'), ('PayPal', 'PayPal')], max_length=20)),
                ('transaction_id', models.CharField(max_length=255)),
                ('booking', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='booking.booking')),
                ('card', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='booking.card')),
            ],
        ),
        migrations.CreateModel(
            name='FlightTicketType',
            fields=[
                ('flight_ticket_types_id', models.AutoField(primary_key=True, serialize=False)),
                ('price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('available_seats', models.IntegerField()),
                ('flight', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='booking.flight')),
                ('ticket_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='booking.tickettype')),
            ],
        ),
        migrations.AddField(
            model_name='card',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='booking.user'),
        ),
        migrations.AddField(
            model_name='booking',
            name='flight_ticket_type',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='booking.flighttickettype'),
        ),
        migrations.AddField(
            model_name='account',
            name='user_id',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='booking.user'),
        ),
    ]
