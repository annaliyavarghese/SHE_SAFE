
from django.urls import path
from . import views
from .views import profile_view


urlpatterns = [
    path("", views.home, name="home"),
    path("login/", views.login_view, name="login"),
    path("register/", views.register_view, name="register"),
    path("logout/", views.logout_view, name="logout"),

    # Profile
    path("profile/", profile_view, name="profile"),
    path("sos-alert/", views.sos_alert, name="sos_alert"),

    # Add emergency contact - only once
    path(
        "add-emergency-contact/",
        views.add_emergency_contact,
        name="add_emergency_contact",
    ),

    # Get saved emergency contact for SOS
    path(
        "api/emergency-contact/",
        views.get_emergency_contact,
        name="get_emergency_contact",
    ),

    # Emergency help
    path(
        "api/emergency-help/",
        views.emergency_help,
        name="emergency_help",
    ),

    # Report issue
    path(
        "report-issue/",
        views.report_issue,
        name="report_issue",
    ),



    

]
