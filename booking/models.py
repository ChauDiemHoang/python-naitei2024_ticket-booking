from django.db import models
from django.utils.translation import gettext_lazy as _
from .constants import (
    MAX_LENGTH_NAME, GENDER_CHOICES, MAX_LENGTH_CHOICES, BOOKING_STATUS,
    STATUS_CHOICES, ROLE_CHOICES, CARD_TYPE_CHOICES, PAYMENT_METHOD_CHOICES, OTP_TIMEOUT
)
from django.utils import timezone
from django.core.validators import RegexValidator, MinLengthValidator
from datetime import date
from django.contrib.auth.models import AbstractUser
import random

class Account(AbstractUser):
    account_id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=MAX_LENGTH_NAME, unique=True, validators=[MinLengthValidator(6), RegexValidator(regex=r"^[\w]+$")])
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Inactive')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='Member')
    first_name = models.CharField(
        max_length=MAX_LENGTH_NAME, verbose_name=_('first name'), null=True)
    last_name = models.CharField(
        max_length=MAX_LENGTH_NAME, verbose_name=_('last name'), null=True)
    gender = models.CharField(
        max_length=MAX_LENGTH_CHOICES,
        choices=GENDER_CHOICES,
        null=True,
        verbose_name=_('gender')
    )
    date_of_birth = models.DateField(default=timezone.now)
    passport_number = models.CharField(max_length=MAX_LENGTH_NAME, unique=True, null=True)
    nationality = models.CharField(max_length=MAX_LENGTH_NAME, default=_('Viet Nam'))

    REQUIRED_FIELDS = ['email', 'phone_number']

    def set_status(self, new_status):
        if new_status in dict(self.STATUS_CHOICES).keys():
            self.status = new_status
            self.save()

    def is_active(self):
        return self.status == 'Active'

    def update_last_login(self):
        self.last_login = timezone.now()
        self.save()

    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"

class Airport(models.Model):
    airport_code = models.CharField(max_length=10, primary_key=True)
    name = models.CharField(max_length=MAX_LENGTH_NAME)
    city = models.CharField(max_length=MAX_LENGTH_NAME)
    country = models.CharField(max_length=MAX_LENGTH_NAME)

    def __str__(self):
        return f"{self.name} ({self.airport_code})"
    
    def get_airports():
        """Retrieve all airports from the database."""
        airports = Airport.objects.all().values("airport_code", "name", "city", "country")
        return list(airports)

class Flight(models.Model):
    flight_id = models.AutoField(primary_key=True)
    flight_number = models.CharField(max_length=MAX_LENGTH_NAME)
    departure_airport = models.ForeignKey(Airport, on_delete=models.CASCADE, related_name='departures')
    arrival_airport = models.ForeignKey(Airport, on_delete=models.CASCADE, related_name='arrivals')
    departure_time = models.DateTimeField()
    arrival_time = models.DateTimeField()

    def get_duration(self):
        """Calculate the flight duration."""
        return self.arrival_time - self.departure_time

    def is_domestic(self):
        """Check if the flight is domestic."""
        return self.departure_airport.country == self.arrival_airport.country

    def has_departed(self):
        """Check if the flight has already departed."""
        return timezone.now() > self.departure_time

    def __str__(self):
        return f"Flight {self.flight_number} from {self.departure_airport} to {self.arrival_airport}"

class TicketType(models.Model):
    ticket_type_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=MAX_LENGTH_NAME)

    def __str__(self):
        return f"{self.name}"

class FlightTicketType(models.Model):
    flight_ticket_types_id = models.AutoField(primary_key=True)
    flight = models.ForeignKey('Flight', on_delete=models.CASCADE)
    ticket_type = models.ForeignKey(TicketType, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    available_seats = models.IntegerField()

    def is_seat_available(self):
        """Check if there are any available seats."""
        return self.available_seats

    def book_seat(self, quantity=1):
        """Book seats if available."""
        if self.is_seat_available():
            self.available_seats -= quantity
            self.save()
            return True
        return False

    def release_seat(self, quantity=1):
        """Release booked seats."""
        self.available_seats += quantity
        self.save()

    def __str__(self):
        return (f"Flight {self.flight.flight_number} - {self.ticket_type.name} "
                f"(Price: {self.price}, Available Seats: {self.available_seats})")

class Card(models.Model):
    card_id = models.AutoField(primary_key=True)
    user = models.ForeignKey('Account', on_delete=models.CASCADE)
    card_number = models.CharField(max_length=16)
    cardholder_name = models.CharField(max_length=MAX_LENGTH_NAME)
    expiry_date = models.DateField()
    card_type = models.CharField(max_length=10, choices=CARD_TYPE_CHOICES)
    billing_address = models.CharField(max_length=MAX_LENGTH_NAME)

    def is_expired(self):
        """Check if the card is expired."""
        return date.today() > self.expiry_date

    def masked_card_number(self):
        """Return the card number masked except for the last 4 digits."""
        return f"**** **** **** {self.card_number[-4:]}"

    def __str__(self):
        return f"{self.cardholder_name} ({self.masked_card_number()}) - {self.get_card_type_display()}"

class Booking(models.Model):
    booking_id = models.AutoField(primary_key=True)
    account = models.ForeignKey('Account', on_delete=models.CASCADE)
    flight_ticket_type = models.ForeignKey('FlightTicketType', on_delete=models.CASCADE)
    booking_date = models.DateTimeField(auto_now_add=True)
    seat_number = models.CharField(max_length=10)
    status = models.CharField(max_length=10, choices=BOOKING_STATUS, default='Confirmed')

    def is_confirmed(self):
        """Check if the booking is confirmed."""
        return self.status == 'Confirmed'

    def total_cost(self):
        """Calculate the total cost of the booking."""
        return self.flight_ticket_type.price

    def __str__(self):
        return (f"Booking {self.booking_id} - {self.account.email} - "
                f"{self.flight_ticket_type.flight.flight_number} - {self.seat_number}")
class Payment(models.Model):
    payment_id = models.AutoField(primary_key=True)
    booking = models.ForeignKey('Booking', on_delete=models.CASCADE)
    card = models.ForeignKey('Card', on_delete=models.CASCADE)
    payment_date = models.DateTimeField(auto_now_add=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    transaction_id = models.CharField(max_length=MAX_LENGTH_NAME)

    def formatted_amount(self):
        """Return the payment amount formatted as a string."""
        return f"${self.amount:.2f}"

    def __str__(self):
        return (f"Payment {self.payment_id} - {self.booking} - "
                f"{self.formatted_amount()} - {self.get_payment_method_display()}")

class Voucher(models.Model):
    voucher_id = models.AutoField(primary_key=True)
    code = models.CharField(max_length=MAX_LENGTH_NAME)
    quantity = models.IntegerField()
    description = models.CharField(max_length=MAX_LENGTH_NAME)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)
    discount_percentage = models.IntegerField()
    expiry_date = models.DateField()

    def is_valid(self):
        """Check if the voucher is valid."""
        return self.quantity > 0 and date.today() <= self.expiry_date

    def calculate_discount(self, price):
        """Calculate the discount amount for a given price."""
        if self.discount_percentage:
            return price * (self.discount_percentage / 100)
        return self.discount_amount

    def __str__(self):
        return f"Voucher {self.code} - {self.description} - Expires on {self.expiry_date}"

class OtpToken(models.Model):
    otp_token_id = models.AutoField(primary_key=True)
    user = models.ForeignKey('Account', on_delete=models.CASCADE)
    otp = models.CharField(max_length=6)
    otp_expires_at = models.DateTimeField()

    def is_expired(self):
        """Check if the OTP token is expired."""
        return timezone.now() > self.otp_expires_at
    
    def generate_otp(self):
        """Generate a random 6-digit OTP."""
        self.otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        self.otp_expires_at = timezone.now() + timezone.timedelta(minutes=OTP_TIMEOUT)
        self.save()
    
    def __str__(self):
        return f"OTP Token {self.otp_token_id} - {self.user.email} - {self.otp}"
