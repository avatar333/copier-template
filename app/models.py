from __future__ import annotations

from datetime import datetime, UTC

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db, login_manager

PET_TYPE_PRODUCTION = "production"
PET_TYPE_NON_PRODUCTION = "non_production"
PET_TYPES = (PET_TYPE_PRODUCTION, PET_TYPE_NON_PRODUCTION)


class AppUser(UserMixin, db.Model):
    __tablename__ = "app_users"

    id = db.Column(db.Integer, primary_key=True)
    login_name = db.Column(db.String(100), nullable=False, unique=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)
    assign_only_pets = db.Column(db.Boolean, nullable=False, default=False)
    assign_only_production_pets = db.Column(db.Boolean, nullable=False, default=False)
    assign_only_non_production_pets = db.Column(db.Boolean, nullable=False, default=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(UTC))
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    pets = db.relationship(
        "PetHost",
        back_populates="owner",
        cascade="all, delete-orphan",
        order_by="(PetHost.pet_type, PetHost.fqdn)",
    )

    assignments = db.relationship("HostAssignment", back_populates="user")
    assignment_runs = db.relationship("AssignmentRun", back_populates="created_by")

    __table_args__ = (
        db.UniqueConstraint("first_name", "last_name", name="uq_app_user_name"),
    )

    @property
    def display_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def full_name(self) -> str:
        return self.display_name

    def __init__(self, **kwargs):
        login_name = kwargs.get("login_name")
        if login_name is not None:
            kwargs["login_name"] = login_name.strip().lower()
        super().__init__(**kwargs)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def assign_only_for_pool(self, pool_name: str | None) -> bool:
        normalized_pool = normalize_pool_name(pool_name)
        if normalized_pool == PET_TYPE_PRODUCTION:
            return bool(self.assign_only_production_pets)
        if normalized_pool == PET_TYPE_NON_PRODUCTION:
            return bool(self.assign_only_non_production_pets)
        return bool(self.assign_only_pets)

    def assign_only_label_for_pool(self, pool_name: str | None) -> str | None:
        normalized_pool = normalize_pool_name(pool_name)
        if normalized_pool == PET_TYPE_PRODUCTION and self.assign_only_production_pets:
            return "Assign ONLY Production Pets"
        if normalized_pool == PET_TYPE_NON_PRODUCTION and self.assign_only_non_production_pets:
            return "Assign ONLY Non-Production Pets"
        if normalized_pool is None and self.assign_only_pets:
            return "Assign ONLY Pets"
        return None


class PetHost(db.Model):
    __tablename__ = "pet_hosts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("app_users.id"), nullable=False)
    pet_type = db.Column(db.String(32), nullable=False, default=PET_TYPE_NON_PRODUCTION)
    fqdn = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(UTC))

    owner = db.relationship("AppUser", back_populates="pets")

    __table_args__ = (
        db.UniqueConstraint("pet_type", "fqdn", name="uq_pet_hosts_pet_type_fqdn"),
    )

    def __init__(self, **kwargs):
        fqdn = kwargs.get("fqdn")
        if fqdn is not None:
            kwargs["fqdn"] = fqdn.strip().lower()
        pet_type = kwargs.get("pet_type")
        if pet_type is not None:
            kwargs["pet_type"] = normalize_pet_type(pet_type)
        super().__init__(**kwargs)

    @property
    def pet_type_label(self) -> str:
        return pet_type_label(self.pet_type)


class HostExclusion(db.Model):
    __tablename__ = "host_exclusions"

    id = db.Column(db.Integer, primary_key=True)
    fqdn = db.Column(db.String(255), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(UTC))
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    created_by_user_id = db.Column(
        db.Integer,
        db.ForeignKey("app_users.id", ondelete="SET NULL"),
        nullable=True,
    )
    updated_by_user_id = db.Column(
        db.Integer,
        db.ForeignKey("app_users.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_by = db.relationship("AppUser", foreign_keys=[created_by_user_id])
    updated_by = db.relationship("AppUser", foreign_keys=[updated_by_user_id])

    def __init__(self, **kwargs):
        fqdn = kwargs.get("fqdn")
        if fqdn is not None:
            kwargs["fqdn"] = fqdn.strip().lower()
        super().__init__(**kwargs)


class AssignmentRun(db.Model):
    __tablename__ = "assignment_runs"

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(UTC))
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("app_users.id"), nullable=True)
    pool_name = db.Column(db.String(50), nullable=True)
    pool_collection_name = db.Column(db.String(100), nullable=True)
    excluded_host_count = db.Column(db.Integer, nullable=False, default=0)
    host_count = db.Column(db.Integer, nullable=False, default=0)
    user_count = db.Column(db.Integer, nullable=False, default=0)
    notes = db.Column(db.Text, nullable=True)

    created_by = db.relationship("AppUser", back_populates="assignment_runs")
    assignments = db.relationship(
        "HostAssignment",
        back_populates="assignment_run",
        cascade="all, delete-orphan",
    )
    warnings = db.relationship(
        "AssignmentWarning",
        back_populates="assignment_run",
        cascade="all, delete-orphan",
    )


class HostAssignment(db.Model):
    __tablename__ = "host_assignments"

    id = db.Column(db.Integer, primary_key=True)
    assignment_run_id = db.Column(
        db.Integer, db.ForeignKey("assignment_runs.id"), nullable=False
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("app_users.id", ondelete="SET NULL"),
        nullable=True,
    )
    fqdn = db.Column(db.String(255), nullable=False)
    source_type = db.Column(db.String(50), nullable=False)
    source_name = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(UTC))

    assignment_run = db.relationship("AssignmentRun", back_populates="assignments")
    user = db.relationship("AppUser", back_populates="assignments")

    __table_args__ = (
        db.UniqueConstraint("assignment_run_id", "fqdn", name="uq_assignment_run_fqdn"),
    )


class AssignmentWarning(db.Model):
    __tablename__ = "assignment_warnings"

    id = db.Column(db.Integer, primary_key=True)
    assignment_run_id = db.Column(
        db.Integer, db.ForeignKey("assignment_runs.id"), nullable=False
    )
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(UTC))

    assignment_run = db.relationship("AssignmentRun", back_populates="warnings")


User = AppUser
Pet = PetHost
AssignmentItem = HostAssignment


def normalize_pet_type(value: str | None) -> str:
    normalized = str(value or "").strip().lower()
    if normalized not in PET_TYPES:
        raise ValueError(f"Unsupported pet type: {value}")
    return normalized


def normalize_pool_name(value: str | None) -> str | None:
    normalized = str(value or "").strip().lower()
    if normalized in {"production", PET_TYPE_PRODUCTION}:
        return PET_TYPE_PRODUCTION
    if normalized in {"non-production", "non_production", PET_TYPE_NON_PRODUCTION}:
        return PET_TYPE_NON_PRODUCTION
    return normalized or None


def pet_type_label(value: str | None) -> str:
    normalized = normalize_pet_type(value)
    if normalized == PET_TYPE_PRODUCTION:
        return "Production"
    return "Non-Production"


@login_manager.user_loader
def load_user(user_id: str) -> AppUser | None:
    return db.session.get(AppUser, int(user_id))
