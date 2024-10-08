from django.shortcuts import render, HttpResponse, HttpResponseRedirect, redirect
from django.urls import reverse
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from .forms import *
from .models import *
from .constants import (
    PRICE_FORMAT, REGEX_PATTERN, REGEX_PATTERN_NAME, 
    REGEX_PATTERN_NUMBER, REGEX_PATTERN_EMAIL, ISO
)
from django.shortcuts import render, get_object_or_404
from .models import Flight, Airport
from django.db.models import Min, Q, F
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from django.views.decorators.csrf import csrf_exempt
from io import BytesIO
from django.template.loader import get_template
from xhtml2pdf import pisa
import secrets
import re


# Create your views here.
def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password"]
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, _("You've been logged in successfully"))
                return HttpResponseRedirect(reverse("index"))
            else:
                messages.error(request, _("Invalid username and/or password"))
                return render(request, "login.html", {'form': form})
        else:
            messages.error(request, _("This username is not valid. Username should contain alphanumeric characters only and have length greater than 6."))
            return render(request, "login.html", {'form': form})
    else:
        form = LoginForm()
        if request.user.is_authenticated:
            return HttpResponseRedirect(reverse("index"))
        else:
            messages.error(request, _("Sign in for various features in the app."))
            return render(request, "login.html", {'form': form})

def register_view(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            try:
                account = form.save(commit=False)
                account.set_password(form.cleaned_data["password"])
                account.save()
            except:
                messages.error(request, _("Username already exists"))
                return render(request, "register.html", {'form': form})
            account = authenticate(request, username=form.cleaned_data["username"], password=form.cleaned_data["password"])
            login(request, account)
            return redirect('index')
        else:
            messages.error(request, _("Information is not valid. Please check information again."))
            return render(request, "register.html", {'form': form})
    else:
        form = SignUpForm()
        return render(request, "register.html", {'form': form})

def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse("login"))

def __get_airports():
    """Retrieve all airports from the database."""
    airports = Airport.objects.all().values("airport_code", "name", "city", "country")
    return list(airports)

def __get_ticket_types():
    """Retrieve all ticket types from the database."""
    ticket_types = TicketType.objects.all().values("ticket_type_id", "name")
    return list(ticket_types)

def __get_available_flights(departure_airport, arrival_airport, departure_date, num_passengers, chair_type_name):
    return Flight.objects.filter(
        departure_airport=departure_airport,
        arrival_airport=arrival_airport,
        departure_time__date=departure_date,
        flighttickettype__available_seats__gte=num_passengers,
        flighttickettype__ticket_type__name=chair_type_name
    ).annotate(
        min_price=Min(
            "flighttickettype__price",
            filter=Q(flighttickettype__available_seats__gte=num_passengers)
        ),
        ticket_type_price=F("flighttickettype__price"),
        ticket_type_available_seats=F("flighttickettype__available_seats")
    ).order_by("min_price")

def __check_datetime(date):
    try:
        parsed_date = parse_date(f"{date}")
        if parsed_date is None:
            return False
    except: 
        return False
    return True

def index(request):
    context = {}
    trip_type = request.GET.get("tripType")
    from_airport = request.GET.get("from")
    to_airport = request.GET.get("to")
    departure_date = request.GET.get("departureDate")
    return_date = request.GET.get("returnDate")
    num_passengers = None
    try:
        num_passengers = int(request.GET.get("numPassengers", 1))  # Default to 1 if not provided
    except:
        context["error_message"] = _("Please use number only for number of passengers.")
    chair_type_name = request.GET.get("chairType")

    context.update({
        "trip_type": trip_type,
        "from_airport": from_airport,
        "to_airport": to_airport,
        "departure_date": departure_date,
        "return_date": return_date,
        "num_passengers": num_passengers,
        "chair_type": chair_type_name,
        "airports": __get_airports(),
        "ticket_types": __get_ticket_types(),
    })

    # If required fields are missing, return to the homepage
    if not from_airport:
        context["error_message"] = _("Please select a departure airport.")
    if not to_airport:
        context["error_message"] = _("Please select an arrival airport.")
    if not departure_date:
        context["error_message"] = _("Please select a departure date.")
    if trip_type == "round" and not return_date:
        context["error_message"] = _("Please select a return date.")
    if not chair_type_name:
        context["error_message"] = _("Please select a chair type.")
    if not num_passengers:
        context["error_message"] = _("Please select the number of passengers.")

    if not from_airport and not to_airport and not departure_date and not return_date and not chair_type_name:
        context["error_message"] = _("Fill in all the fields to search for your flights.")

    elif trip_type != "round" and trip_type != "oneway":
        context["error_message"] = _("The trip type is not valid.")

    elif (departure_date and not __check_datetime(departure_date)) or (trip_type == "round" and return_date and not __check_datetime(return_date)):
        context["error_message"] = _("The date is not valid.")

    elif not re.match(REGEX_PATTERN_NUMBER, str(num_passengers)):
        context["error_message"] = _("The number of passengers is not valid.")
    
    else:
        # If departure and destination are the same, return to the homepage
        if from_airport and to_airport and from_airport == to_airport:
            context["error_message"] = _("Departure and destination airports cannot be the same.")

        if return_date and departure_date and trip_type == "round" and return_date <= departure_date:
            context["error_message"] = _("Return date cannot be less than departure date.")

        if departure_date and parse_datetime(f"{departure_date}T23:59:59+0000") < timezone.now():
            context["error_message"] = _("You cannot book flights from the past.")

        if request.user.is_authenticated and request.user.status != 'Active':
            context["error_message"] = _("You need to activate your account first.")

    if context.get("error_message"):
        return render(request, "homepage.html", context)

    # Filter flights by chair type and available seats
    departure_flights = __get_available_flights(from_airport, to_airport, departure_date, num_passengers, chair_type_name)
    if not departure_flights:
        context["error_message"] = _("No flights available with the selected criteria. Please try again.")
        return render(request, "homepage.html", context)

    context["departure_flights"] = departure_flights
    for flight in departure_flights:
        flight.ticket_type_price = PRICE_FORMAT.format(flight.ticket_type_price)

    # If round trip, get return flights with the same conditions
    if trip_type == "round":
        return_flights = __get_available_flights(to_airport, from_airport, return_date, num_passengers, chair_type_name)
        if not return_flights:
            context["error_message"] = _("No return flights available with the selected criteria. Please try again.")
            return render(request, "homepage.html", context)
        context["return_flights"] = return_flights
        for flight in return_flights:
            flight.ticket_type_price = PRICE_FORMAT.format(flight.ticket_type_price)

    return render(request, "homepage.html", context)

def flight_detail(request, flight_id):
    flight = get_object_or_404(Flight, flight_id=flight_id)
    departure_airport = flight.departure_airport
    arrival_airport = flight.arrival_airport
    
    context = {
        'flight': flight,
        'departure_airport': departure_airport,
        'arrival_airport': arrival_airport,
    }
    
    return render(request, 'flight_detail.html', context)

def flight_list(request):
    flights = Flight.objects.all()
    departure_date = request.GET.get('departure_date')
    if departure_date:
        flights = flights.filter(departure_time__date=departure_date)
    departure_location = request.GET.get('departure_location')
    if departure_location:
        flights = flights.filter(departure_airport__city=departure_location)
    airports = Airport.objects.values_list('city', flat=True).distinct()
    context = {
        'flights': flights,
        'airports': airports,
    }
    return render(request, 'flight_list.html', context)
@login_required
def user_bookings(request):
    bookings = Booking.objects.filter(account=request.user)
    return render(request, 'user_bookings.html', {'bookings': bookings})

@login_required
def cancel_booking(request, booking_id):
    booking = get_object_or_404(Booking, booking_id=booking_id)

    if booking.account != request.user:
        messages.error(request, _("You do not have permission to cancel this booking."))
        return redirect('user_bookings')
    
    booking.set_status('PendingCancellation')
    booking.save()
    messages.success(request, _("Your booking cancellation request has been submitted and is pending approval."))

    return redirect('user_bookings')
def is_admin(user):
    return user.is_superuser
@login_required
@user_passes_test(is_admin, '/booking/logout')
def pending_cancellations(request):
    bookings = Booking.objects.filter(status="PendingCancellation")
    return render(request, 'pending_cancellations.html', {'bookings': bookings})

@login_required
@user_passes_test(is_admin, '/booking/logout')
def approve_cancellation(request, booking_id):
    booking = get_object_or_404(Booking, booking_id=booking_id)
    pending_cancellation_status = dict(BOOKING_STATUS)['PendingCancellation']
    if booking.status != pending_cancellation_status:
        messages.error(request, _("This booking cannot be approved."))
        return redirect('pending_cancellations')
    booking.set_status("Canceled")  
    booking.flight_ticket_type.release_seat(int(booking.seat_number))
    booking.save()
    messages.success(request, _("Cancellation approved successfully."))
    return redirect('pending_cancellations')

@login_required
@user_passes_test(is_admin, '/booking/logout')
def reject_cancellation(request, booking_id):
    booking = get_object_or_404(Booking, booking_id=booking_id)
    pending_cancellation_status = dict(BOOKING_STATUS)['PendingCancellation']
    if booking.status != pending_cancellation_status :
        messages.error(request, _("This booking cannot be rejected."))
        return redirect('pending_cancellations')
    booking.set_status("DeniedCancellation")  
    booking.save()
    messages.success(request, _("Cancellation rejected."))
    return redirect('pending_cancellations')

def is_active(user):
    if not user.is_authenticated:
        return False
    if user.status == _('Active'):
        return True
    return False

@user_passes_test(is_active, '/booking/login')
def book_infor_view(request):
    flight_1 = request.GET.get('d_flight_id')
    seat = request.GET.get('flight_ticket_type')
    round_trip = False
    if request.GET.get('r_flight_id'):
        round_trip = True

    if round_trip:
        flight_2 = request.GET.get('r_flight_id')
    
    numPassengers = request.GET.get('num_passengers')
    if not numPassengers or not flight_1 or not seat or (round_trip and not flight_2):
        messages.error(request, _("Too few information."))
        return redirect(reverse('index'))
    elif not re.match(REGEX_PATTERN_NUMBER, numPassengers):
        messages.error(request, _("Invalid number of passengers."))
        return redirect(reverse('index'))

    if request.user.is_authenticated:
        try:
            flight1 = Flight.objects.get(flight_id=flight_1)
        except:
            messages.error(request, _("Flight ID is not valid."))
            return redirect(reverse('index'))
        try:
            flight1type = FlightTicketType.objects.get(flight_id=flight_1, ticket_type__name=seat)
        except:
            messages.error(request, _("Seat type is not valid."))
            return redirect(reverse('index'))
        flight1price = flight1type.price
        if int(numPassengers) > int(flight1type.available_seats):
            messages.error(request, _("Number of passengers is too large."))
            return redirect(reverse('index')) 
        flight1ddate = flight1.departure_time.date
        flight1adate = flight1.arrival_time.date
        if flight1.departure_time <= timezone.now():
            messages.error(request, _("You cannot book flight from the past."))
            return redirect(reverse('index'))
        flight2 = None
        flight2ddate = None
        flight2adate = None
        if round_trip:
            try:
                flight2 = Flight.objects.get(flight_id=flight_2)
            except:
                messages.error(request, _("Flight ID is not valid."))
                return redirect(reverse('index'))
            try:
                flight2type = FlightTicketType.objects.get(flight_id=flight_2, ticket_type__name=seat)
            except:
                messages.error(request, _("Seat type is not valid."))
                return redirect(reverse('index'))
            flight2price = flight2type.price
            if int(numPassengers) > int(flight2type.available_seats):
                messages.error(request, _("Number of passengers is too large."))
                return redirect(reverse('index'))
            flight2ddate = flight2.departure_time.date
            flight2adate = flight2.arrival_time.date
            if flight2.departure_airport.airport_code != flight1.arrival_airport.airport_code:
                messages.error(request, _("Airports are mismatch."))
                return redirect(reverse('index'))
            elif flight2.arrival_airport.airport_code != flight1.departure_airport.airport_code:
                messages.error(request, _("Airports are mismatch."))
                return redirect(reverse('index'))
            elif flight2.departure_time <= flight1.arrival_time:
                messages.error(request, _("Return flight is sooner than departure flight."))
                return redirect(reverse('index'))
            elif flight2.departure_time <= timezone.now():
                messages.error(request, _("You cannot book flight from the past."))
                return redirect(reverse('index'))
            return render(request, "book_infor.html", {
                'flight1': flight1,
                'flight2': flight2,
                "flight1ddate": flight1ddate,
                "flight1adate": flight1adate,
                "flight2ddate": flight2ddate,
                "flight2adate": flight2adate,
                "seat": seat,
                "num_passengers": request.GET.get('num_passengers'),
                "passengers": list(range(int(request.GET.get('num_passengers')))),
                "price": PRICE_FORMAT.format(float(flight1price) + float(flight2price)),
                "total_price": PRICE_FORMAT.format((float(flight1price) + float(flight2price)) * int(request.GET.get('num_passengers'))),
                "phone_number": request.user.phone_number[1:],
                "email": request.user.email,
                "real_price": (float(flight1price) + float(flight2price)) * int(request.GET.get('num_passengers'))
            })
        return render(request, "book_infor.html", {
            'flight1': flight1,
            "flight1ddate": flight1ddate,
            "flight1adate": flight1adate,
            "seat": seat,
            "num_passengers": request.GET.get('num_passengers'),
            "passengers": list(range(int(request.GET.get('num_passengers')))),
            "price": PRICE_FORMAT.format(float(flight1price)),
            "total_price": PRICE_FORMAT.format(float(flight1price) * int(request.GET.get('num_passengers'))),
            "phone_number": request.user.phone_number[1:],
            "email": request.user.email,
            "real_price": float(flight1price) * int(request.GET.get('num_passengers'))
        })
    else:
        return redirect(reverse("login"))

def __create_ticket(user, passengers, passengerscount, flight, flight_class, countrycode, mobile, email):
    booking = Booking.objects.create(
        account=user, 
        flight_ticket_type=FlightTicketType.objects.get(flight=flight, ticket_type__name=flight_class)
    )
    booking.seat_number = passengerscount
    for passenger in passengers:
        booking.passengers.add(passenger)
    flightTicket = FlightTicketType.objects.get(flight=flight, ticket_type__name=flight_class)
    booking.flight_ticket_type = flightTicket
    phone_number = f"0{mobile}"
    booking.account.phone_number = phone_number
    booking.account.email = email
    booking.account.save()
    booking.save()
    return booking

@user_passes_test(is_active, '/booking/login')
def payment_view(request):
    if request.method == 'POST':
        if request.user.is_authenticated:
            proceed = True
            flight_1 = request.POST.get('flight1')
            flight_1class = request.POST.get('flight1Class')
            f2 = False
            if request.POST.get('flight2'):
                flight_2 = request.POST.get('flight2')
                flight_2class = request.POST.get('flight2Class')
                f2 = True
            countrycode = request.POST['countryCode']
            if not countrycode:
                messages.error(request, _("Please select a country code."))
                proceed = False
            mobile = request.POST['mobile']
            if not mobile:
                messages.error(request, _("Please input your phone number."))
                proceed = False
            if mobile and not re.match(REGEX_PATTERN_NUMBER, mobile):
                messages.error(request, _("Your phone number is not valid."))
                proceed = False
            email = request.POST['email']
            if not email:
                messages.error(request, _("Please input your email."))
                proceed = False
            elif not re.match(REGEX_PATTERN_EMAIL, email):
                messages.error(request, _("Your email is not valid."))
                proceed = False
            try:
                flight1 = Flight.objects.get(flight_id=flight_1)
                if flight1.departure_time <= timezone.now():
                    raise ValidationError("Flight from the past.")
            except:
                messages.error(request, _("The departure flight is not valid."))
                proceed = False
            if f2:
                try:
                    flight2 = Flight.objects.get(flight_id=flight_2)
                    if flight2.departure_time <= timezone.now():
                        raise ValidationError("Flight from the past.")
                    elif flight2.departure_airport != flight1.arrival_airport or flight2.arrival_airport != flight1.departure_airport:
                        raise ValidationError("Airport mismatch.")
                    elif flight2.departure_time <= flight1.arrival_time:
                        raise ValidationError("Flight 2 is sooner than flight 1.")
                except:
                    messages.error(request, _("The return flight is not valid."))
                    proceed = False
            passengerscount = request.POST['numPassengers']
            passengers=[]
            coupon = request.POST.get('coupon')
            price = request.POST.get('totalCost')
            try:
                for i in range(int(passengerscount)):
                    fname = request.POST[f'passenger{i}Fname']
                    if not fname:
                        messages.error(request, _("Please input the first names."))
                        proceed = False
                    elif not re.match(REGEX_PATTERN_NAME, fname):
                        messages.error(request, _("Some of the first names are not valid."))
                        proceed = False
                    lname = request.POST[f'passenger{i}Lname']
                    if not lname:
                        messages.error(request, _("Please input the last names."))
                        proceed = False
                    elif not re.match(REGEX_PATTERN_NAME, lname):
                        messages.error(request, _("Some of the last names are not valid."))
                        proceed = False
                    gender = request.POST[f'passenger{i}Gender']
                    if not gender:
                        messages.error(request, _("Please select the genders."))
                        proceed = False
                    elif gender not in [_("Male"), _("Female"), _("Other")]:
                        messages.error(request, _("Some of the genders are not valid."))
                        proceed = False
                    dob = request.POST[f'passenger{i}DateOfBirth']
                    if not dob:
                        messages.error(request, _("Please input the dates of birth."))
                        proceed = False
                    elif not __check_datetime(dob):
                        messages.error(request, _("Some of the dates of birth are not valid."))
                        proceed = False
                    elif parse_datetime(f"{dob}T23:59:59+0000") >= timezone.now():
                        messages.error(request, _("The dates of birth should be prior to today."))
                        proceed = False 
                    nationality = request.POST[f'passenger{i}Nationality']
                    if flight1.departure_airport.country != flight1.arrival_airport.country:
                        passno = request.POST[f'passenger{i}PassportNumber']
                        if not passno:
                            messages.error(request, _("Please input the passport numbers."))
                            proceed = False
                        elif not re.match(REGEX_PATTERN, passno):
                            messages.error(request, _("Some of the passport numbers are not valid."))
                            proceed = False
                        coi = request.POST[f'passenger{i}CountryOfIssue']
                        expire = request.POST[f'passenger{i}PassportExpireDate']
                        if not expire:
                            messages.error(request, _("Please input the passport expire dates."))
                            proceed = False
                        elif not __check_datetime(expire):
                            messages.error(request, _("Some of the expire dates are not valid."))
                            proceed = False
                        if parse_datetime(f"{expire}T23:59:59+0000") <= timezone.now():
                            messages.error(request, _("Some of the passports are not usable anymore."))
                            proceed = False
                    else:
                        passno = 'None'
                        coi = 'None'
                        expire = timezone.now()
                    if proceed:
                        passengers.append(Passenger.objects.create(
                            first_name=fname,
                            last_name=lname,
                            gender=gender.capitalize(),
                            date_of_birth=dob,
                            nationality=nationality,
                            passport_number=passno,
                            passport_from_country=coi,
                            due_date=expire
                        ))
                if not proceed:
                    return redirect(request.META.get('HTTP_REFERER', '/'))
                ticket1 = __create_ticket(request.user,passengers,passengerscount,flight1,flight_1class,countrycode,mobile,email)
                price = str(float(ticket1.flight_ticket_type.price))
                if f2:
                    ticket2 = __create_ticket(request.user,passengers,passengerscount,flight2,flight_2class,countrycode,mobile,email)
                    price = str(float(ticket1.flight_ticket_type.price) + float(ticket2.flight_ticket_type.price))
            except Exception as e:
                messages.error(request, _("Your information is not valid. Please try again."))
                return redirect(request.META.get('HTTP_REFERER', '/'))

            if f2:    ##
                return render(request, "payment.html", {
                    "ticket1": ticket1.booking_id,
                    "ticket2": ticket2.booking_id,
                    "price": PRICE_FORMAT.format(float(price)),
                    "real_price": price
                })  ##
            return render(request, "payment.html", {
                "ticket1": ticket1.booking_id,
                "price": PRICE_FORMAT.format(float(price)),
                "real_price": price
            })
        else:
            return HttpResponseRedirect(reverse("login"))
    else:
        return redirect(reverse('index'))

@user_passes_test(is_active, '/booking/login')
def process_view(request):
    if request.user.is_authenticated:
        if request.method == 'POST':
            proceed = True
            ticket1_id = request.POST['ticket1']
            ticket = None
            try:
                ticket = Booking.objects.get(booking_id=ticket1_id)
            except:
                messages.error(request, _('This ticket is not exist.'))
                proceed = False
            if ticket and (ticket.status != _('PendingCancellation') or ticket.account != request.user):
                messages.error(request, _('This ticket is not valid.'))
                proceed = False   
            t2 = False
            if request.POST.get('ticket2'):
                ticket2_id = request.POST['ticket2']
                ticket2 = None
                try:
                    ticket2 = Booking.objects.get(booking_id=ticket2_id)
                except:
                    messages.error(request, _('This ticket is not exist.'))
                    proceed = False
                t2 = True
                if ticket2 and (ticket2.status != _('PendingCancellation') or ticket2.account != request.user):
                    messages.error(request, _('This ticket is not valid.'))
                    proceed = False
            fare = '-1'
            if t2 and ticket and ticket2:
                fare = str((float(ticket.flight_ticket_type.price) + float(ticket2.flight_ticket_type.price)) * int(ticket.seat_number))
            elif not t2 and ticket:
                fare = str(float(ticket.flight_ticket_type.price) * int(ticket.seat_number))
            card_number = request.POST['cardNumber']
            if not card_number:
                messages.error(request, _("Please input your card number."))
                proceed = False
            elif not re.match(REGEX_PATTERN_NUMBER, card_number):
                messages.error(request, _("Your card number is not valid. It must contain numbers only."))
                proceed = False
            elif len(card_number) >= 20:
                messages.error(request, _("Your card number is not valid. Its length must be less than 20."))
                proceed = False
            card_holder_name = request.POST['cardHolderName']
            if not card_holder_name:
                messages.error(request, _("Please input your card holder's name."))
                proceed = False
            elif not re.match(REGEX_PATTERN_NAME, card_holder_name):
                messages.error(request, _("Your card holder's name is not valid."))
                proceed = False
            validdate = True
            exp_month = request.POST['expMonth']
            if not exp_month:
                messages.error(request, _("Please select your card's expire month."))
                proceed = False
                validdate = False
            elif not re.match(REGEX_PATTERN_NUMBER, exp_month) or (re.match(REGEX_PATTERN_NUMBER, exp_month) and int(exp_month) not in range(1, 13)):
                messages.error(request, _("Your expire month is not valid."))
                proceed = False
                validdate = False
            exp_year = request.POST['expYear']
            if not exp_year:
                messages.error(request, _("Please select your card's expire year."))
                proceed = False
                validdate = False
            elif not re.match(REGEX_PATTERN_NUMBER, exp_year) or (re.match(REGEX_PATTERN_NUMBER, exp_year) and int(exp_year) not in range(2024, 2061)):
                messages.error(request, _("Your expire year is not valid."))
                proceed = False
                validdate = False
            if validdate and parse_datetime(f"{exp_year}-{exp_month}-01T23:59:59+0000") <= timezone.now():
                messages.error(request, _("Your card is expired. Please choose another card."))
                proceed = False
            elif validdate:
                expiry_date = parse_date(f"{exp_year}-{exp_month}-01")
            card_type = request.POST['cardType']
            if not card_type:
                messages.error(request, _("Please select your card's type."))
                proceed = False
            elif card_type not in [_("Visa"), _("MasterCard")]:
                messages.error(request, _("Your card's type is not valid."))
                proceed = False
            if not proceed:
                if t2:
                    return render(request, 'payment.html', {
                        "ticket1": ticket1_id,
                        "ticket2": ticket2_id,
                        "price": PRICE_FORMAT.format(float(fare)),
                        "real_price": fare
                    })
                return render(request, 'payment.html', {
                    "ticket1": ticket1_id,
                    "price": PRICE_FORMAT.format(float(fare)),
                    "real_price": fare
                })
            try:
                card = Card.objects.filter(user=request.user).exists()
                if card:
                    card = Card.objects.get(user=request.user)
                else:
                    card = Card.objects.create(user=request.user, expiry_date=timezone.now())
                card.card_number = card_number
                card.card_type = card_type
                card.cardholder_name = card_holder_name
                card.expiry_date = expiry_date
                card.save()

                ticket = Booking.objects.get(booking_id=ticket1_id)
                ticket.status = 'Confirmed'
                ticket.booking_date = timezone.now()
                ticket.flight_ticket_type.book_seat(int(ticket.seat_number))
                ticket.flight_ticket_type.save()
                ticket.save()
                payment = Payment.objects.filter(booking=ticket).exists()
                if payment:
                    payment = Payment.objects.get(booking=ticket)
                else:
                    payment = Payment.objects.create(booking=ticket,card=card,amount=fare)
                    payment.transaction_id = secrets.token_hex(3).upper()
                payment.card = card
                payment.amount = fare
                payment.payment_method = 'Credit Card'
                id1 = payment.transaction_id
                payment.save()
                if t2:
                    ticket2 = Booking.objects.get(booking_id=ticket2_id)
                    ticket2.status = 'Confirmed'
                    ticket2.booking_date = timezone.now()
                    ticket2.flight_ticket_type.book_seat(int(ticket2.seat_number))
                    ticket2.flight_ticket_type.save()
                    ticket2.save()
                    payment2 = Payment.objects.filter(booking=ticket2).exists()
                    if payment2:
                        payment2 = Payment.objects.get(booking=ticket2)
                    else:
                        payment2 = Payment.objects.create(booking=ticket2,card=card,amount=fare)
                        payment2.transaction_id = secrets.token_hex(3).upper()
                    payment2.card = card
                    payment2.amount = fare
                    payment2.payment_method = 'Credit Card'
                    id2 = payment2.transaction_id
                    payment2.save()
                    return render(request, 'payment_process.html', {
                        'ticket1': ticket,
                        'ticket2': ticket2,
                        'ref1': id1,
                        'ref2': id2
                    })
                return render(request, 'payment_process.html', {
                    'ticket1': ticket,
                    'ticket2': "",
                    'ref1': id1,
                    'ref2': ""
                })
            except Exception as e:
                return HttpResponse(e)
        else:
            return redirect(reverse('index'))
    else:
        return HttpResponseRedirect(reverse('login'))

def render_to_pdf(template_src, context_dict={}):
    template = get_template(template_src)
    html = template.render(context_dict)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode(ISO)), result)
    if not pdf.err:
        return HttpResponse(result.getvalue(), content_type='application/pdf')
    return None

@csrf_exempt
@user_passes_test(is_active, '/booking/login')
def print_ticket(request, booking_id):
    ticket = Booking.objects.get(booking_id=booking_id)
    payment = Payment.objects.get(booking_id=booking_id)
    flight = ticket.flight_ticket_type.flight
    is_foreign = False
    for passenger in ticket.passengers.all():
        if passenger.passport_number != 'None':
            is_foreign = True
            break
    data = {
        'ticket': ticket,
        'payment': payment,
        'flight': flight,
        'is_foreign': is_foreign,
        'current_year': timezone.now().year,
        'initial_price': PRICE_FORMAT.format(float(ticket.flight_ticket_type.price)),
        'total_price': PRICE_FORMAT.format(float(ticket.flight_ticket_type.price) 
                                           * int(ticket.seat_number))
    }
    pdf = render_to_pdf('ticket.html', data)
    return HttpResponse(pdf, content_type='application/pdf')
