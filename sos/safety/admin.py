from django.contrib import admin

# Register your models here.
from .models import (
    EmergencyContact,
    TrustedContact,
    SOSAlert,
    SafetyReport,
)

admin.site.register(EmergencyContact)
admin.site.register(TrustedContact)
admin.site.register(SOSAlert)
admin.site.register(SafetyReport)