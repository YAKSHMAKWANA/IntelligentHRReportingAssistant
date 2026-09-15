from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator

from rest_framework.views import APIView
from rest_framework.response import Response


# =========================================================
# CSRF TOKEN
# =========================================================

@method_decorator(ensure_csrf_cookie, name="dispatch")
class CSRFTokenAPIView(APIView):
    def get(self, request):
        return Response({
            "success": True
        })


# =========================================================
# REGISTER
# =========================================================

@method_decorator(ensure_csrf_cookie, name="dispatch")
class RegisterAPIView(APIView):

    def post(self, request):

        username = request.data.get(
            "username",
            ""
        ).strip()

        password = request.data.get(
            "password",
            ""
        ).strip()


        # Username validation
        if not username:
            return Response(
                {
                    "success": False,
                    "error": "Username is required."
                },
                status=400
            )


        # Password validation
        if not password:
            return Response(
                {
                    "success": False,
                    "error": "Password is required."
                },
                status=400
            )


        # Minimum password length
        if len(password) < 6:
            return Response(
                {
                    "success": False,
                    "error": "Password must be at least 6 characters."
                },
                status=400
            )


        # Check existing username
        if User.objects.filter(
            username=username
        ).exists():

            return Response(
                {
                    "success": False,
                    "error": "Username already exists."
                },
                status=400
            )


        # Create user
        user = User.objects.create_user(
            username=username,
            password=password
        )


        # Login immediately after registration
        login(
            request,
            user
        )


        return Response(
            {
                "success": True,
                "message": "Account created successfully.",
                "user": {
                    "id": user.id,
                    "username": user.username
                }
            },
            status=201
        )


# =========================================================
# LOGIN
# =========================================================

@method_decorator(ensure_csrf_cookie, name="dispatch")
class LoginAPIView(APIView):

    def post(self, request):

        username = request.data.get(
            "username",
            ""
        ).strip()

        password = request.data.get(
            "password",
            ""
        ).strip()


        # Empty fields
        if not username or not password:

            return Response(
                {
                    "success": False,
                    "error": "Username and password are required."
                },
                status=400
            )


        # Authenticate user
        user = authenticate(
            request,
            username=username,
            password=password
        )


        # Invalid credentials
        if user is None:

            return Response(
                {
                    "success": False,
                    "error": "Invalid username or password."
                },
                status=401
            )


        # Create Django session
        login(
            request,
            user
        )


        return Response(
            {
                "success": True,
                "message": "Login successful.",
                "user": {
                    "id": user.id,
                    "username": user.username
                }
            }
        )


# =========================================================
# LOGOUT
# =========================================================

@method_decorator(ensure_csrf_cookie, name="dispatch")
class LogoutAPIView(APIView):

    def post(self, request):

        logout(request)

        return Response(
            {
                "success": True,
                "message": "Logout successful."
            }
        )