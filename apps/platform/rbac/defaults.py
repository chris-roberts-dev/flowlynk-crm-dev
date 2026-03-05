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
    "owner": {
        "name": "Owner",
        "description": "Full access within the organization.",
        "is_system": True,
        "is_active": True,
        "capabilities": list(CAPABILITIES.keys()),
    },
    "manager": {
        "name": "Manager",
        "description": "Operational manager: locations, leads, quotes, tasks.",
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
            "rbac.assign",
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
}
