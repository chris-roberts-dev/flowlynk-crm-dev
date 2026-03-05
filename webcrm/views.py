from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from apps.platform.accounts.models import Membership, User
from apps.platform.organizations.models import Organization
from webcrm.forms import EmailDiscoveryForm, TenantPasswordOnlyLoginForm


PENDING_EMAIL_SESSION_KEY = "pending_login_email"


class LandingPageView(TemplateView):
    template_name = "landing.html"


class EmailDiscoveryView(View):
    def get(self, request: HttpRequest) -> HttpResponse:
        form = EmailDiscoveryForm()
        return render(request, "login_email.html", {"form": form})

    def post(self, request: HttpRequest) -> HttpResponse:
        form = EmailDiscoveryForm(request.POST)
        if not form.is_valid():
            return render(request, "login_email.html", {"form": form})

        email = form.cleaned_data["email"].strip().lower()

        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if not user:
            messages.error(request, "No active memberships were found for that email.")
            return render(request, "login_email.html", {"form": form})

        # Platform superuser: go straight to platform admin login
        if user.is_superuser:
            return redirect("/admin/login/?next=/admin/")

        memberships = (
            Membership.objects.select_related("organization")
            .filter(
                user=user,
                status=Membership.Status.ACTIVE,
                organization__status=Organization.Status.ACTIVE,
            )
            .order_by("organization__name")
        )

        if not memberships.exists():
            messages.error(request, "No active memberships were found for that email.")
            return render(request, "login_email.html", {"form": form})

        # Store pending email for the next step (password-only login page)
        request.session[PENDING_EMAIL_SESSION_KEY] = email

        if memberships.count() == 1:
            org_slug = memberships[0].organization.slug
            return redirect("tenant-login", org_slug=org_slug)

        org_choices = [
            {"name": m.organization.name, "slug": m.organization.slug}
            for m in memberships
        ]
        return render(
            request, "org_picker.html", {"email": email, "org_choices": org_choices}
        )


class ClearPendingLoginView(View):
    def post(self, request: HttpRequest) -> HttpResponse:
        request.session.pop(PENDING_EMAIL_SESSION_KEY, None)
        return redirect("email-discovery")


class TenantAdminEntrypointView(View):
    """
    /t/<org_slug>/admin/ sets tenant affinity in session and redirects to /admin/.

    This avoids subdomain cookies/CSRF issues by keeping everything on one host.
    """

    def get(self, request: HttpRequest, org_slug: str) -> HttpResponse:
        org = (
            Organization.objects.filter(
                slug=org_slug, status=Organization.Status.ACTIVE
            )
            .only("id", "slug", "name", "status")
            .first()
        )
        if not org:
            raise Http404("Organization not found.")

        request.session["active_org_id"] = org.id
        request.session["active_org_slug"] = org.slug

        # Redirect into admin on same host; middleware will resolve tenant from session.
        return redirect("/admin/")


class TenantLoginView(View):
    def get(self, request: HttpRequest, org_slug: str) -> HttpResponse:
        org = getattr(request, "organization", None)
        if org is None or org.slug != org_slug:
            raise Http404("Tenant not resolved")

        email = request.session.get(PENDING_EMAIL_SESSION_KEY)
        if not email:
            return redirect("email-discovery")

        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if not user:
            request.session.pop(PENDING_EMAIL_SESSION_KEY, None)
            return redirect("email-discovery")

        has_access = Membership.objects.filter(
            user=user,
            organization=org,
            status=Membership.Status.ACTIVE,
        ).exists()
        if not has_access:
            messages.error(request, "You do not have access to this organization.")
            request.session.pop(PENDING_EMAIL_SESSION_KEY, None)
            return redirect("email-discovery")

        form = TenantPasswordOnlyLoginForm()
        return render(
            request,
            "tenant_login.html",
            {"form": form, "organization": org, "email": email},
        )

    def post(self, request: HttpRequest, org_slug: str) -> HttpResponse:
        org = getattr(request, "organization", None)
        if org is None or org.slug != org_slug:
            raise Http404("Tenant not resolved")

        email = request.session.get(PENDING_EMAIL_SESSION_KEY)
        if not email:
            return redirect("email-discovery")

        form = TenantPasswordOnlyLoginForm(request.POST)
        if not form.is_valid():
            return render(
                request,
                "tenant_login.html",
                {"form": form, "organization": org, "email": email},
            )

        password = form.cleaned_data["password"]

        user = authenticate(request, username=email, password=password)
        if user is None:
            messages.error(request, "Invalid password.")
            return render(
                request,
                "tenant_login.html",
                {"form": form, "organization": org, "email": email},
            )

        membership = Membership.objects.filter(
            user=user,
            organization=org,
            status=Membership.Status.ACTIVE,
        ).first()
        if not membership:
            messages.error(request, "You do not have access to this organization.")
            request.session.pop(PENDING_EMAIL_SESSION_KEY, None)
            return redirect("email-discovery")

        login(request, user)
        request.session["active_org_id"] = org.id
        request.session["active_org_slug"] = org.slug

        membership.last_login_at = timezone.now()
        membership.save(update_fields=["last_login_at"])

        request.session.pop(PENDING_EMAIL_SESSION_KEY, None)

        # ✅ Same-host redirect: no subdomain cookies; user enters password once.
        return redirect("/admin/")


class TenantAppHomeView(TemplateView):
    template_name = "tenant_app_home.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        org = getattr(self.request, "organization", None)
        if org is None:
            raise Http404("Tenant not resolved")
        ctx["organization"] = org
        return ctx
