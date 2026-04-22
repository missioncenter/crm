from django.contrib import admin
from django.contrib.auth import logout
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect


def logout_view(request):
    logout(request)
    return redirect("/accounts/login/")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/logout/", logout_view, name="logout"),
    path("accounts/", include("django.contrib.auth.urls")),
    path("", include("projects.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
