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
    # Only allow a single label as org slug (no nested subdomains like a.b.app.com)
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
    Resolves tenant context early and applies admin boundary rules.

    Priority:
      1) Subdomain: {org}.{TENANT_BASE_DOMAIN}
      2) Explicit path: /login/{org_slug}
      3) Session fallback: active_org_id
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

        # Session fallback (only if not resolved already)
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

        # If tenant is required and missing:
        # - for /admin/, redirect to /login/ (better UX than 404)
        # - for other tenant-required routes, keep 404 to reduce surface area
        if self._path_requires_tenant(path) and request.organization is None:  # type: ignore[attr-defined]
            if path.startswith("/admin/"):
                return redirect("/login/")
            raise Http404("Tenant not resolved")

        # Admin boundary: if accessing /admin/ with a tenant, enforce membership unless platform superuser
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
                        # Hard fail safe: logout + clear tenant session; redirect to discovery
                        if hasattr(request, "session"):
                            request.session.pop("active_org_id", None)
                            request.session.pop("active_org_slug", None)
                        logout(request)
                        return redirect("/login/")

                # If we resolved tenant via host/path and user is authenticated, align session to this org
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
