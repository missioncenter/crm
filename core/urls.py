from django.contrib import admin
from django.contrib.auth import logout
from django.urls import include, path
from pathlib import Path
from django.conf import settings
from django.conf.urls.static import static
from django.http import FileResponse, Http404
from django.shortcuts import redirect

BASE_DIR = Path(__file__).resolve().parent.parent


def logout_view(request):
    logout(request)
    return redirect("/accounts/login/")


def favicon_view(request):
    favicon_path = BASE_DIR / "favicon.ico"
    try:
        return FileResponse(open(favicon_path, "rb"), content_type="image/x-icon")
    except FileNotFoundError:
        raise Http404

urlpatterns = [
    path("favicon.ico", favicon_view),
    path("admin/", admin.site.urls),
    path("accounts/logout/", logout_view, name="logout"),
    path("accounts/", include("django.contrib.auth.urls")),
    path("", include("projects.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
