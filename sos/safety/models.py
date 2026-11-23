from django.db import models

# Create your models here.
# models.py

from django.db import models
from django.contrib.auth.models import User


class EmergencyContact(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="emergency_contacts"
    )
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    relationship = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.user.username}"


class TrustedContact(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="trusted_contacts"
    )
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    relationship = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return f"{self.name} - {self.user.username}"


class SOSAlert(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="sos_alerts"
    )
    message = models.TextField(default="Emergency help requested")
    latitude = models.CharField(max_length=50, blank=True)
    longitude = models.CharField(max_length=50, blank=True)
    maps_link = models.URLField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"SOS - {self.user.username} - {self.created_at}"


class SafetyReport(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="safety_reports"
    )
    category = models.CharField(max_length=100, blank=True)
    title = models.CharField(max_length=200, blank=True)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title or f"Safety report #{self.pk}"