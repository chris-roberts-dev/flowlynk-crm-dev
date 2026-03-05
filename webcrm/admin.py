from __future__ import annotations

from django.apps import apps as django_apps
from django.contrib.admin import AdminSite
from django.contrib.auth import views as auth_views
from django.http import HttpRequest
from django.urls import path


class FlowLynkAdminSite(AdminSite):
    site_header = "FlowLynk Admin"
    site_title = "FlowLynk Admin"
    index_title = "Administration"

    def get_urls(self):
        urls = super().get_urls()
        # Override logout to always go to landing page
        custom = [
            path(
                "logout/",
                self.admin_view(auth_views.LogoutView.as_view(next_page="/")),
                name="logout",
            ),
        ]
        return custom + urls

    def get_grouped_app_list(self, request: HttpRequest) -> dict[str, list[dict]]:
        app_list = super().get_app_list(request)

        platform_apps: list[dict] = []
        crm_apps: list[dict] = []

        for app_dict in app_list:
            app_label = app_dict.get("app_label")
            try:
                app_config = django_apps.get_app_config(app_label)
                app_path = app_config.name
            except LookupError:
                app_path = ""

            if app_path.startswith("apps.platform."):
                platform_apps.append(app_dict)
            else:
                crm_apps.append(app_dict)

        return {"Platform": platform_apps, "CRM": crm_apps}

    def each_context(self, request: HttpRequest) -> dict:
        context = super().each_context(request)
        context["grouped_app_list"] = self.get_grouped_app_list(request)
        return context


admin_site = FlowLynkAdminSite(name="flowlynk_admin")
