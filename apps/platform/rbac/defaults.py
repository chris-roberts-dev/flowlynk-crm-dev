from __future__ import annotations

CAPABILITIES: dict[str, str] = {
    # RBAC
    "rbac.manage": "Manage roles and role-to-capability mappings.",
    "rbac.assign": "Assign roles and capability grants to memberships.",
    # Locations / Catalog
    "locations.manage": "Manage regions/markets/locations (create/update/import).",
    "catalog.import": "Import catalog items and manage catalog definitions.",
    # Leads / Quotes / Clients
    "leads.view": "View leads.",
    "leads.manage": "Create/update leads and run qualification steps.",
    "leads.convert": "Convert leads to quotes/clients.",
    "quotes.view": "View quotes.",
    "quotes.manage": "Create/update quotes and versions.",
    "quotes.approve": "Approve quotes (if approval workflow enabled).",
    # Pricing / Tasks / Comms
    "pricing.preview": "Generate pricing previews and snapshots.",
    "tasks.assign": "Assign tasks to team members.",
    "tasks.complete": "Complete/close tasks.",
    "communications.view": "View communications threads and records.",
    "communications.send": "Send communications (email/sms) via platform adapters.",
    # Routing / Audit
    "routes.manage": "Manage routing boards and density workflows.",
    "audit.view": "View audit log entries.",
}


ROLE_TEMPLATES: dict[str, dict] = {
    # ---- Full control ----
    "owner": {
        "name": "Owner",
        "description": "Full access within the organization.",
        "is_system": True,
        "is_active": True,
        "capabilities": list(CAPABILITIES.keys()),
    },
    # ---- Management tiers (MVP uses same capability set; later we scope by region/market/location) ----
    "regional_manager": {
        "name": "Regional Manager",
        "description": "Manage operations across a region (MVP: org-wide manager privileges).",
        "is_system": True,
        "is_active": True,
        "capabilities": [
            "locations.manage",
            "catalog.import",
            "leads.view",
            "leads.manage",
            "leads.convert",
            "quotes.view",
            "quotes.manage",
            "quotes.approve",
            "pricing.preview",
            "tasks.assign",
            "tasks.complete",
            "communications.view",
            "routes.manage",
            "audit.view",
            # Regional managers may assign roles, but not edit role definitions
            "rbac.assign",
        ],
    },
    "market_manager": {
        "name": "Market Manager",
        "description": "Manage operations across a market (MVP: org-wide manager privileges).",
        "is_system": True,
        "is_active": True,
        "capabilities": [
            "locations.manage",
            "catalog.import",
            "leads.view",
            "leads.manage",
            "leads.convert",
            "quotes.view",
            "quotes.manage",
            "pricing.preview",
            "tasks.assign",
            "tasks.complete",
            "communications.view",
            "routes.manage",
            "audit.view",
            "rbac.assign",
        ],
    },
    "location_manager": {
        "name": "Location Manager",
        "description": "Manage a specific location (MVP: org-wide manager privileges).",
        "is_system": True,
        "is_active": True,
        "capabilities": [
            "locations.manage",
            "leads.view",
            "leads.manage",
            "leads.convert",
            "quotes.view",
            "quotes.manage",
            "pricing.preview",
            "tasks.assign",
            "tasks.complete",
            "communications.view",
            "routes.manage",
        ],
    },
    # ---- Functional roles ----
    "sales": {
        "name": "Sales",
        "description": "Sales workflow: leads/quotes/pricing and customer communications.",
        "is_system": True,
        "is_active": True,
        "capabilities": [
            "leads.view",
            "leads.manage",
            "leads.convert",
            "quotes.view",
            "quotes.manage",
            "pricing.preview",
            "communications.view",
            "communications.send",
            "tasks.complete",
        ],
    },
    "ops": {
        "name": "Ops",
        "description": "Operations workflow: tasks, routing, and internal comms visibility.",
        "is_system": True,
        "is_active": True,
        "capabilities": [
            "locations.manage",
            "tasks.assign",
            "tasks.complete",
            "routes.manage",
            "communications.view",
        ],
    },
    "staff": {
        "name": "Staff",
        "description": "General staff: view leads/quotes, complete tasks.",
        "is_system": True,
        "is_active": True,
        "capabilities": [
            "leads.view",
            "quotes.view",
            "tasks.complete",
            "communications.view",
        ],
    },
    "viewer": {
        "name": "Viewer",
        "description": "Read-only access to key areas.",
        "is_system": True,
        "is_active": True,
        "capabilities": [
            "leads.view",
            "quotes.view",
            "communications.view",
            "audit.view",
        ],
    },
}
