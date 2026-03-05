from django.contrib.auth import views as auth_views
from django.urls import path

from webcrm.admin import admin_site
from webcrm.views import (
    ClearPendingLoginView,
    EmailDiscoveryView,
    LandingPageView,
    TenantAdminEntrypointView,
    TenantAppHomeView,
    TenantLoginView,
)

urlpatterns = [
    path("", LandingPageView.as_view(), name="landing"),
    path("login/", EmailDiscoveryView.as_view(), name="email-discovery"),
    path("login/clear/", ClearPendingLoginView.as_view(), name="clear-pending-login"),
    path("login/<slug:org_slug>/", TenantLoginView.as_view(), name="tenant-login"),
    # ✅ New: path-based tenant admin entrypoint
    path(
        "t/<slug:org_slug>/admin/",
        TenantAdminEntrypointView.as_view(),
        name="tenant-admin-entry",
    ),
    path("logout/", auth_views.LogoutView.as_view(next_page="/"), name="logout"),
    path("app/", TenantAppHomeView.as_view(), name="tenant-app-home"),
    path("admin/", admin_site.urls),
]
