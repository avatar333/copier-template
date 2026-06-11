from __future__ import annotations

import re
from typing import Iterable

from sqlalchemy.exc import SQLAlchemyError

from ..extensions import db
from ..models import HostExclusion

FQDNISH_RE = re.compile(
    r"^(?=.{1,253}$)(?!-)[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.(?!-)[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+$"
)


def get_excluded_host_fqdns() -> set[str]:
    try:
        return {exclusion.fqdn for exclusion in HostExclusion.query.order_by(HostExclusion.fqdn).all()}
    except SQLAlchemyError:
        return set()


def get_host_exclusion_text() -> str:
    return "\n".join(sorted(get_excluded_host_fqdns()))


def parse_host_exclusion_lines(raw_values: str | None) -> tuple[list[str], list[str]]:
    if not raw_values:
        return [], []

    seen = set()
    values: list[str] = []
    errors: list[str] = []
    for line in raw_values.splitlines():
        fqdn = line.strip().lower()
        if not fqdn:
            continue
        if not FQDNISH_RE.match(fqdn):
            errors.append(f"Invalid FQDN value: {fqdn}")
            continue
        if fqdn in seen:
            continue
        seen.add(fqdn)
        values.append(fqdn)
    return values, errors


def replace_host_exclusions(fqdns: Iterable[str], user_id: int | None) -> None:
    db.session.query(HostExclusion).delete(synchronize_session=False)
    for fqdn in fqdns:
        db.session.add(
            HostExclusion(
                fqdn=fqdn,
                created_by_user_id=user_id,
                updated_by_user_id=user_id,
            )
        )
