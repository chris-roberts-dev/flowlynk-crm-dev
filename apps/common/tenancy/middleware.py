from __future__ import annotations

import re
from typing import Optional

from django.conf import settings
from django.contrib.auth import logout
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.utils.deprecation import MiddlewareMixin

from apps.common.tenancy.context import set_current_org_id
from apps.platform.accounts.models import Membership
from apps.platform.organizations.models import Organization

SLUG_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")


def _clean_host(host: str) -> str:
    host = (host or "").strip().lower()
    if ":" in host:
        host = host.split(":", 1)[0]
    host = host.rstrip(".")
    return host


def _extract_org_slug_from_host(host: str) -> Optional[str]:
    base = getattr(settings, "TENANT_BASE_DOMAIN", "")
    host = _clean_host(host)
    if not host or not base:
        return None

    base = _clean_host(base)
    if host == base:
        return None

    suffix = f".{base}"
    if not host.endswith(suffix):
        return None

    slug = host[: -len(suffix)]
    if "." in slug:
        return None
    if not SLUG_RE.match(slug):
        return None
    return slug


def _extract_org_slug_from_path(request: HttpRequest) -> Optional[str]:
    path = request.path_info or ""
    if not path.startswith("/login/"):
        return None
    remainder = path[len("/login/") :]
    slug = remainder.split("/", 1)[0].strip().lower()
    if not slug:
        return None
    if not SLUG_RE.match(slug):
        return None
    return slug


class TenantResolutionMiddleware(MiddlewareMixin):
    """
    Priority:
      1) Subdomain
      2) /login/{org_slug}
      3) Session fallback: active_org_id
    Platform superuser:
      - may access /admin/ without tenant context (platform mode)
    """

    def process_request(self, request: HttpRequest) -> Optional[HttpResponse]:
        request.organization = None  # type: ignore[attr-defined]
        set_current_org_id(None)

        path = request.path_info or ""

        # Resolve tenant by host/path first
        slug = _extract_org_slug_from_host(request.get_host())
        if slug is None:
            slug = _extract_org_slug_from_path(request)

        org: Organization | None = None
        resolved_by_host_or_path = False

        if slug:
            org = (
                Organization.objects.filter(
                    slug=slug, status=Organization.Status.ACTIVE
                )
                .only("id", "slug", "name", "status")
                .first()
            )
            if org:
                resolved_by_host_or_path = True

        # Session fallback
        if org is None and hasattr(request, "session"):
            org_id = request.session.get("active_org_id")
            if isinstance(org_id, int):
                org = (
                    Organization.objects.filter(
                        id=org_id, status=Organization.Status.ACTIVE
                    )
                    .only("id", "slug", "name", "status")
                    .first()
                )

        if org:
            request.organization = org  # type: ignore[attr-defined]
            set_current_org_id(org.id)

        # Tenant-required enforcement
        if self._path_requires_tenant(path) and request.organization is None:
            # Allow Django Admin to handle unauthenticated redirect to /admin/login/
            if (
                path.startswith("/admin/")
                and getattr(request, "user", None) is not None
            ):
                user = request.user
                if not user.is_authenticated:
                    return None  # let admin redirect to /admin/login/?next=/admin/
                if user.is_superuser:
                    return None  # platform-wide admin mode (authenticated superuser)

                # Authenticated non-superuser without tenant -> send to discovery
                return redirect("/login/")

            # Non-admin tenant-required routes remain deny-by-default
            raise Http404("Tenant not resolved")

        # Admin boundary for non-superusers in tenant mode
        if path.startswith("/admin/") and not self._is_exempt(path):
            org = getattr(request, "organization", None)
            if org is not None and getattr(request, "user", None) is not None:
                user = request.user
                if user.is_authenticated and not user.is_superuser:
                    has_access = Membership.objects.filter(
                        user_id=user.id,
                        organization_id=org.id,
                        status=Membership.Status.ACTIVE,
                    ).exists()
                    if not has_access:
                        if hasattr(request, "session"):
                            request.session.pop("active_org_id", None)
                            request.session.pop("active_org_slug", None)
                        logout(request)
                        return redirect("/login/")

                # Align session to host/path tenant for authenticated users
                if (
                    user.is_authenticated
                    and resolved_by_host_or_path
                    and hasattr(request, "session")
                ):
                    request.session["active_org_id"] = org.id
                    request.session["active_org_slug"] = org.slug

        return None

    @staticmethod
    def _is_exempt(path: str) -> bool:
        prefixes = getattr(settings, "TENANT_EXEMPT_PATH_PREFIXES", [])
        return any(path.startswith(p) for p in prefixes)

    @classmethod
    def _path_requires_tenant(cls, path: str) -> bool:
        if cls._is_exempt(path):
            return False
        prefixes = getattr(settings, "TENANT_REQUIRED_PATH_PREFIXES", [])
        return any(path.startswith(p) for p in prefixes)
