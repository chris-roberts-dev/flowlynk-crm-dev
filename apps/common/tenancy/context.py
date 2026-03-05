from __future__ import annotations

import contextvars
from contextlib import contextmanager
from typing import Iterator, Optional

_current_org_id: contextvars.ContextVar[Optional[int]] = contextvars.ContextVar(
    "current_org_id",
    default=None,
)


def set_current_org_id(org_id: int | None) -> None:
    _current_org_id.set(org_id)


def get_current_org_id() -> int | None:
    return _current_org_id.get()


class TenantNotResolvedError(RuntimeError):
    pass


def require_current_org_id() -> int:
    org_id = get_current_org_id()
    if org_id is None:
        raise TenantNotResolvedError(
            "Tenant context is not resolved (current_org_id is None)."
        )
    return org_id


@contextmanager
def org_context(org_id: int | None) -> Iterator[None]:
    token = _current_org_id.set(org_id)
    try:
        yield
    finally:
        _current_org_id.reset(token)
