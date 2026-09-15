from django.urls import path

from .views import (
    CSRFTokenAPIView,
    RegisterAPIView,
    LoginAPIView,
    LogoutAPIView,
)


urlpatterns = [

    # CSRF
    path(
        "csrf/",
        CSRFTokenAPIView.as_view(),
        name="csrf"
    ),

    # Authentication
    path(
        "register/",
        RegisterAPIView.as_view(),
        name="register"
    ),

    path(
        "login/",
        LoginAPIView.as_view(),
        name="login"
    ),

    path(
        "logout/",
        LogoutAPIView.as_view(),
        name="logout"
    ),
]