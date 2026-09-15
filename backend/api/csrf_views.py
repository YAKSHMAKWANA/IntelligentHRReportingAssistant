from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie


@ensure_csrf_cookie
def csrf_token(request):
    """
    Return a CSRF token to the frontend.

    The frontend runs on Vercel and the backend runs on Render,
    so the token is returned explicitly as JSON instead of relying
    on document.cookie.
    """
    return JsonResponse(
        {
            "success": True,
            "csrfToken": get_token(request),
        }
    )