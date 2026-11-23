
import json
import re

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_GET, require_POST

from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from .models import (
    EmergencyContact,
    TrustedContact,
    SOSAlert,
    SafetyReport,
)

# HOME
def home(request):
    if request.user.is_authenticated:
        return render(request, "dashboard.html")

    return redirect("login")

# LOGIN
@csrf_protect
def login_view(request):

    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":

        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        saved_user = User.objects.filter(
            username__iexact=username
        ).first()

        user = None

        if saved_user:
            user = authenticate(
                request,
                username=saved_user.username,
                password=password,
            )

        if user is not None:
            login(request, user)
            return redirect("home")

        messages.error(
            request,
            "Invalid username or password. Please try again."
        )

    return render(request, "login.html")

# REGISTER
@csrf_protect
def register_view(request):

    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":

        full_name = request.POST.get("full_name", "").strip()
        email = request.POST.get("email", "").strip()
        username = request.POST.get("username", "").strip()

        password1 = request.POST.get("password1", "")
        password2 = request.POST.get("password2", "")

        emergency_name = request.POST.get(
            "emergency_name", ""
        ).strip()

        emergency_phone = request.POST.get(
            "emergency_phone", ""
        ).strip()

        emergency_relationship = request.POST.get(
            "emergency_relationship", ""
        ).strip()

        # Required fields
        if not all([
            full_name,
            email,
            username,
            password1,
            password2,
            emergency_name,
            emergency_phone,
        ]):

            messages.error(
                request,
                "Please fill in all required fields."
            )

            return render(
                request,
                "login.html",
                {"show_register": True}
            )

        # Password match
        if password1 != password2:

            messages.error(
                request,
                "Passwords do not match."
            )

            return render(
                request,
                "login.html",
                {"show_register": True}
            )

        # Password length
        if len(password1) < 8:

            messages.error(
                request,
                "Password must contain at least 8 characters."
            )

            return render(
                request,
                "login.html",
                {"show_register": True}
            )

        # Duplicate username
        if User.objects.filter(
            username__iexact=username
        ).exists():

            messages.error(
                request,
                "This username is already taken."
            )

            return render(
                request,
                "login.html",
                {"show_register": True}
            )

        # Duplicate email
        if User.objects.filter(
            email__iexact=email
        ).exists():

            messages.error(
                request,
                "This email is already registered."
            )

            return render(
                request,
                "login.html",
                {"show_register": True}
            )

        # Phone validation
        if not re.fullmatch(
            r"[0-9+\-\s()]{7,20}",
            emergency_phone
        ):

            messages.error(
                request,
                "Please enter a valid emergency contact number."
            )

            return render(
                request,
                "login.html",
                {"show_register": True}
            )

        # Create user and emergency contact
        try:

            with transaction.atomic():

                name_parts = full_name.split()

                first_name = name_parts[0]
                last_name = " ".join(name_parts[1:])

                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password1,
                    first_name=first_name,
                    last_name=last_name,
                )

                EmergencyContact.objects.create(
                    user=user,
                    name=emergency_name,
                    phone=emergency_phone,
                    relationship=emergency_relationship,
                )

        except Exception:

            messages.error(
                request,
                "Registration could not be completed. Please try again."
            )

            return render(
                request,
                "login.html",
                {"show_register": True}
            )

        messages.success(
            request,
            "Your SheSafe account was created successfully. "
            "Please log in."
        )

        return redirect("login")

    return render(request, "login.html")

# LOGOUT
def logout_view(request):

    logout(request)

    return redirect("home")

# ADD EMERGENCY CONTACT
@login_required
def add_emergency_contact(request):

    if request.method == "POST":

        name = request.POST.get("name", "").strip()
        phone = request.POST.get("phone", "").strip()

        relationship = request.POST.get(
            "relationship", ""
        ).strip()

        if not name or not phone:

            messages.error(
                request,
                "Name and phone number are required."
            )

        elif not re.fullmatch(
            r"[0-9+\-\s()]{7,20}",
            phone
        ):

            messages.error(
                request,
                "Please enter a valid phone number."
            )

        else:

            EmergencyContact.objects.create(
                user=request.user,
                name=name,
                phone=phone,
                relationship=relationship,
            )

            messages.success(
                request,
                "Emergency contact added successfully!"
            )

            return redirect("profile")

    return redirect("profile")

# SEND SOS SMS FUNCTION
def send_sos_sms(user, maps_link, message):

    contacts = EmergencyContact.objects.filter(user=user)

    if not contacts.exists():
        return 0, 0, "No emergency contacts found."

    account_sid = getattr(settings, "TWILIO_ACCOUNT_SID", None)
    auth_token = getattr(settings, "TWILIO_AUTH_TOKEN", None)
    from_number = getattr(settings, "TWILIO_PHONE_NUMBER", None)

    if not all([account_sid, auth_token, from_number]):
        return 0, contacts.count(), "Twilio settings are missing. Check your .env file."

    try:
        client = Client(account_sid, auth_token)
    except Exception as e:
        print("Could not initialize Twilio:", str(e))
        return 0, contacts.count(), "Could not initialize Twilio."

    location_text = maps_link or "Location is not available."

    sms_body = (
        f"SHESAFE EMERGENCY: "
        f"{user.get_full_name() or user.username} needs help. "
        f"{message} Location: {location_text}"
    )

    sent_count = 0
    failed_count = 0

    for contact in contacts:
        try:
            client.messages.create(
                body=sms_body,
                from_=from_number,
                to=contact.phone.strip()
                
            )
            sent_count += 1

        except TwilioRestException as e:
            failed_count += 1
            print("Twilio Error Code:", e.code)
            print("Twilio Error Message:", e.msg)
            print("Contact ID:", contact.pk)

        except Exception as e:
            failed_count += 1
            print("SMS failed for contact ID:", contact.pk, str(e))

    if sent_count == 0:
        return (
            0,
            failed_count,
            "SMS could not be sent to any emergency contact. Check the Twilio error in terminal."
        )

    return sent_count, failed_count, None

# EMERGENCY HELP - MAIN SOS API
@login_required
@require_POST
def emergency_help(request):

    try:
        data = json.loads(request.body or "{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse(
            {"success": False, "message": "Invalid JSON data."},
            status=400
        )

    message = str(
        data.get("message") or "Emergency help requested"
    ).strip()

    latitude = str(data.get("latitude") or "").strip()
    longitude = str(data.get("longitude") or "").strip()
    maps_link = str(data.get("maps_link") or "").strip()

    # Create Google Maps link if not received
    if not maps_link and latitude and longitude:
        maps_link = (
            f"https://www.google.com/maps?q="
            f"{latitude},{longitude}"
        )

    # Save SOS alert in database
    alert = SOSAlert.objects.create(
        user=request.user,
        message=message,
        latitude=latitude,
        longitude=longitude,
        maps_link=maps_link,
    )

    # Send SMS to saved emergency contacts
    sent_count, failed_count, error_message = send_sos_sms(
        request.user,
        maps_link,
        message
    )

    if sent_count == 0:
        return JsonResponse(
            {
                "success": False,
                "message": error_message,
                "alert_id": alert.pk
            },
            status=502
        )

    response_message = (
        f"SOS SMS sent to {sent_count} emergency contact(s)."
    )

    if failed_count:
        response_message += (
            f" {failed_count} contact(s) could not be reached."
        )

    return JsonResponse(
        {
            "success": True,
            "message": response_message,
            "alert_id": alert.pk,
            "sent_count": sent_count,
            "failed_count": failed_count,
        },
        status=200
    )

# SOS ALERT - FORM ENDPOINT
@login_required
@require_POST
def sos_alert(request):

    location = request.POST.get(
        "location", ""
    ).strip()

    message = "Emergency help requested"

    alert = SOSAlert.objects.create(
        user=request.user,
        message=message,
        maps_link=location,
    )

    sent_count, failed_count, error_message = send_sos_sms(
        request.user,
        location,
        message
    )

    if sent_count == 0:

        return JsonResponse(
            {
                "status": "error",
                "message": error_message,
                "alert_id": alert.pk
            },
            status=502
        )

    return JsonResponse(
        {
            "status": "success",
            "message": (
                f"SOS SMS sent to {sent_count} contact(s)."
            ),
            "failed_count": failed_count,
            "alert_id": alert.pk
        }
    )

# REPORT ISSUE
@login_required
@require_POST
def report_issue(request):

    category = request.POST.get(
        "category", ""
    ).strip()

    title = request.POST.get(
        "title", ""
    ).strip()

    description = request.POST.get(
        "description", ""
    ).strip()

    if not description:

        description = (
            request.POST.get("message", "").strip()
            or request.POST.get("report", "").strip()
        )

    if not description:

        return JsonResponse(
            {
                "error": "Please enter a description."
            },
            status=400
        )

    report = SafetyReport.objects.create(
        user=request.user,
        category=category,
        title=title,
        description=description,
    )

    return JsonResponse(
        {
            "message": "Your report has been submitted.",
            "report_id": report.pk
        },
        status=201
    )

# ADD TRUSTED CONTACT
@login_required
@require_POST
def add_trusted_contact(request):

    name = request.POST.get(
        "name", ""
    ).strip()

    phone = request.POST.get(
        "phone", ""
    ).strip()

    relationship = request.POST.get(
        "relationship", ""
    ).strip()

    if not name or not phone:

        return JsonResponse(
            {
                "error": "Name and phone are required."
            },
            status=400
        )

    contact = TrustedContact.objects.create(
        user=request.user,
        name=name,
        phone=phone,
        relationship=relationship,
    )

    return JsonResponse(
        {
            "message": "Trusted contact saved.",
            "id": contact.pk
        },
        status=201
    )

# PROFILE
@login_required
def profile_view(request):

    emergency_contacts = EmergencyContact.objects.filter(
        user=request.user
    ).order_by("id")

    context = {
        "emergency_contacts": emergency_contacts
    }

    return render(
        request,
        "profile.html",
        context
    )

# GET EMERGENCY CONTACT
@login_required
@require_GET
def get_emergency_contact(request):

    contact = EmergencyContact.objects.filter(
        user=request.user
    ).order_by("id").first()

    if not contact:

        return JsonResponse(
            {
                "error": "No emergency contact found."
            },
            status=404
        )

    return JsonResponse(
        {
            "name": contact.name,
            "phone": contact.phone,
            "relationship": contact.relationship
        }
    )