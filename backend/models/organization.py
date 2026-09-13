from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base


class OfficeType(StrEnum):
    HO = "HO"
    CO = "CO"
    RO = "RO"
    BRANCH = "BRANCH"


class OrganizationUnit(Base):
    __tablename__ = "organization_units"
    __table_args__ = (
        CheckConstraint("parent_id IS NULL OR parent_id <> id", name="parent_not_self"),
        CheckConstraint(
            "(office_type = 'HO' AND parent_id IS NULL) OR "
            "(office_type <> 'HO' AND parent_id IS NOT NULL)",
            name="ho_parent_rule",
        ),
        Index("ix_organization_units_parent_active", "parent_id", "is_active"),
        Index("ix_organization_units_type_active", "office_type", "is_active"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    office_type: Mapped[OfficeType] = mapped_column(
        Enum(
            OfficeType,
            name="office_type",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            length=10,
        ),
        nullable=False,
    )
    parent_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("organization_units.id", ondelete="RESTRICT"),
        nullable=True,
    )
    state: Mapped[str | None] = mapped_column(String(100))
    district: Mapped[str | None] = mapped_column(String(100))
    city: Mapped[str | None] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    parent: Mapped[OrganizationUnit | None] = relationship(
        "OrganizationUnit",
        remote_side=[id],
        back_populates="children",
    )
    children: Mapped[list[OrganizationUnit]] = relationship(
        "OrganizationUnit",
        back_populates="parent",
    )


class OrganizationHierarchy(Base):
    """Closure table used for fast RBAC ancestor/descendant checks."""

    __tablename__ = "organization_hierarchy"
    __table_args__ = (
        CheckConstraint("depth >= 0", name="non_negative_depth"),
        CheckConstraint(
            "(depth = 0 AND ancestor_id = descendant_id) OR "
            "(depth > 0 AND ancestor_id <> descendant_id)",
            name="depth_matches_relationship",
        ),
        Index("ix_organization_hierarchy_descendant_depth", "descendant_id", "depth"),
    )

    ancestor_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("organization_units.id", ondelete="CASCADE"),
        primary_key=True,
    )
    descendant_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("organization_units.id", ondelete="CASCADE"),
        primary_key=True,
    )
    depth: Mapped[int] = mapped_column(Integer, nullable=False)
