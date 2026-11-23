
from twilio.rest import Client
from django.conf import settings


def send_emergency_sms(phone, location):

    client = Client(
        settings.TWILIO_ACCOUNT_SID,
        settings.TWILIO_AUTH_TOKEN
    )

    message = client.messages.create(
        body=f"EMERGENCY! I need help. My location: {location}",
        from_=settings.TWILIO_PHONE_NUMBER,
        to=phone
    )

    return message.sid
