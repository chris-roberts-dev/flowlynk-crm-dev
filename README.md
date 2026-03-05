# Overview of FlowLynk CRM
## Product Intent
FlowLynk is a Django + Postgres multi-tenant SaaS CRM for service + sales businesses, optimized for:
- Admin-first operations: Django Admin is the MVP UI (fast data entry, imports, bulk actions, auditability)
- Tenant safety by default: row-based multi-tenancy with strict isolation and leak prevention
- Workflow integrity: predictable lifecycle flows (Lead → Quote → Client; Pricing snapshot previews; Tasks/Comms triggers)
- Franchise/territory readiness: location hierarchy, recurring service scheduling, route density and routing boards
- Auditability + guardrails: sensitive actions require reason, append-only audit trail, immutable pricing snapshots

## Multi-tenancy model (non-negotiable)
- Row-based tenancy (no schema-per-tenant), with absolute tenant isolation
- Every tenant-owned record must be scoped by:
    - direct `organization_id`, or
    - mandatory FK chain ending at a tenant root (validated for org consistency)
- Tenant must be resolved before any tenant data access
- Tenant resolution priority:
    - Subdomain: `{org_slug}.app.com` (or `{org_slug}.localhost` in dev)
    - Explicit path: `/login/{org_slug}`
    - Root domain email discovery → find memberships → redirect or org picker
- Session is tenant-scoped even if identity is global

## Identity + auth philosophy
- User is global (one identity, multiple org memberships)
- Membership is tenant-scoped (user↔org, status, last_login_at)
- Tenant login is email discovery first, then password-only after org selection
- Platform users (superusers) have distinct platform login and cross-tenant access

## Security architecture
- RBAC is enforced server-side in service layer and in admin model access (admin is not the security boundary)
- Deny-by-default when tenant unresolved on tenant routes
- Guard against host-header attacks & invalid subdomain patterns
- Prevent cross-tenant joins unless explicit platform privilege

## Admin-first MVP strategy
- Django Admin is the primary interface
- Custom AdminSite groups apps into only:
    - Platform (apps.platform.*)
    - CRM (everything else)
- Tenant admins should see tenant-relevant models (Users filtered by tenant, Memberships, Roles, Locations, etc.)

--- 

# Detailed list of what’s completed to date
## Foundation / Infrastructure
- Project skeleton and required folder layout created
- Settings modules: `base.py`, `dev.py`, `prod.py`
- `.env` loading + `.env.example`
- Postgres via `DATABASE_URL`
- Basic landing page + Bootstrap 5 template
- Admin mounted at `/admin/`
- pytest + pytest-django running; tests green

## Admin grouping (Platform vs CRM)
- Custom `AdminSite` implementation
- `get_app_list()` overridden to group apps into two headings only
- Admin index template override to render those two groupings
- Visibility still respects permissions (no leakage)

## Multi-tenancy: resolution + enforcement
- Tenant resolution middleware:
    - resolves org from subdomain
    - supports `/login/{org_slug}` explicit path
    - supports email discovery on root domain
- Tenant stored on `request.organization` + tenant-scoped session state
- Deny-by-default for tenant-required routes when tenant unresolved
- Host header guardrails (invalid/nested patterns rejected)
- Tests for tenant resolution and denial cases

## Tenant-scoped ORM & admin scoping
- Tenant-aware managers/querysets; “unscoped” escape hatch for system tasks/tests
- Admin querysets tenant-filtered
- Admin save hooks force `organization` and audit fields (`created_by`, `updated_by`)
- Tests proving tenant scoping and forced org on create

## Auth flow & UX
- Landing page has separate buttons for:
    - Tenant login (email discovery)
    - Platform login
- Email discovery flow:
    - email entry → membership lookup
    - single org → go straight to org login step
    - multi org → org picker
- Org login step asks only for password (email carried via session)
- “Not you?” clears pending login email
- Logout redirects (platform + tenant admin) return to landing page
- Tests around discovery, org selection, logout redirects

## RBAC core
- RBAC models built (global Capability; tenant Role; mappings; membership grants)
- Capability seeding command (`seed_capabilities`) idempotent
- Role import from JSON:
    - idempotent upsert by (`org`, `role.code`)
    - capability validation
    - `--dry-run` support
    - deterministic replace of mappings

## RBAC enforcement in admin
- Admin permission mixin requiring capability per action (`view/add/change/delete`)
- Wired into key tenant models (Locations, Roles, Grants, etc.)
- Tests updated/added so admin requires both:
    - Django model permissions
    - RBAC capability

## Bootstrap tooling for org admins
- `bootstrap_org_admin` command:
    - creates org + user + membership if needed
    - ensures owner role template exists + assigned
    - ensures tenant admin can see models in Django admin by granting Django perms by ContentType (no label mismatch)
    - sets `is_staff=True`
    - idempotent; tests green
- Admin action “Make Org Owner (RBAC)” on Memberships:
    - assigns owner
    - ensures staff and Django perms so models appear

---

# Detailed remaining items (roadmap / backlog for co-development)
This is the “what’s left”.

## EPIC 2 — Tenancy hardening & invariants
- Tenant filtering for UserAdmin (tenant admins should only see users with membership in that org)
- Cross-tenant FK validation patterns:
    - enforce org consistency on FK chains (model clean + DB constraints where possible)
- Tenant-safe admin features:
    - autocomplete endpoints tenant-filtered
    - raw_id_fields / FK dropdowns prevent cross-tenant selection
- Stronger middleware route classification:
    - clear list of platform-only paths
    - clear list of tenant-required paths
    - ensure no tenant access on root domain except login discovery
- “Platform mode” concepts:
    - explicit platform-only views/tools (support, diagnostics)
    - rules for when platform can bypass tenant scoping

## EPIC 3 — Audit foundation (high value early)
- `AuditEvent` append-only model:
    - org-scoped or platform-scoped depending on event type
    - correlation_id, actor, IP/UA, request_id, metadata JSON
- “Reason required” enforcement:
    - for sensitive actions (role changes, grants, imports, impersonation later)
- Admin UX for audit:
    - filters, search, export
- Emit audit events for:
    - role assignment changes
    - grants changes
    - import applies
    - pricing approvals later

## EPIC 4 — Import framework (generalized)
- `ImportRun` model:
    - org, entity_type, status, dry_run flag, counts, errors, created_by, timestamps
- Common import engine utilities:
    - parse + validate
    - diff/preview
    - idempotent apply
- Locations import using ImportRun
- Catalog import using ImportRun

## EPIC 5 — Locations hierarchy (beyond single Location)
- Add Region → Market → Location hierarchy
- Constraints:
    - `(org, code)` uniqueness for each
    - required FK chain with org consistency checks
- Admin UX:
    - inlines, filters, bulk import action

## EPIC 6 — Catalog
- Catalog entities:
    - Service, AddOn, Bundle, ChecklistTemplate (and checklist items)
- Soft delete for catalog items
- Import engine for catalog
- Admin UX optimized for fast editing

## EPIC 7 — Leads → Quotes → Clients workflow
- Lead model:
    - intake fields, status, source, tags
    - conversion methods in service layer
    - RBAC capabilities: view/manage/convert
- Quote model:
    - versions, line items, totals
    - approval status, accept/decline lifecycle
    - RBAC capabilities: view/manage/approve
- Client model:
    - contacts, service addresses, agreements/plans (soft delete where appropriate)
- Conversion flows:
    - lead → quote conversion
    - quote accepted → client + plan
- Tests for conversions + tenant isolation

## EPIC 8 — Pricing engine + snapshots
- PricingVersion, PricingRule, PricingEngine service
- PricingSnapshot:
    - immutable inputs/outputs/rationale JSON
    - line items + totals; created_by; timestamps
- Preview endpoints in service layer
- Guardrails:
    - no cross-tenant data references
    - snapshot immutability enforcement
- Tests:
    - preview output stability
    - snapshot immutability

## EPIC 9 — Tasks + Communications
- Unified Task model:
    - status, due_at, assigned_to, entity references
- Task triggers:
    - on lead creation, quote sent, quote accepted, etc.
- Communications:
    - threads + comm records
    - link to entities
    - ability to create tasks from comms
- Admin UX:
    - work queue view, filters, bulk actions
- Tests for triggers and visibility

## EPIC 10 — Ops (Scheduling / Routing / Quality)
- VisitPlan → VisitInstance generation (rolling horizon job)
- Assignments
- Routing board + density metrics
- Quality checklists + issues + rework loop
- Exception queues

## EPIC 11 — Reporting
- KPI models / query services
- Export utilities
- Later: background aggregation jobs/materialized views

## Cross-cutting (continue throughout)
- More tenant leak tests (ORM + admin + service layer)
- DB indexing/constraints expansion across all new models
- Soft delete pattern implementation where required
- Hardening of platform superuser “see everything” while preventing accidental tenant leaks