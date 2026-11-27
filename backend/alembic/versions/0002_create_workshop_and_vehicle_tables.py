from collections.abc import Sequence
from datetime import datetime

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

BAY_TYPES = ("GENERAL", "LIFT", "DIAGNOSTIC", "TIRES")


def timestamp_columns() -> list[sa.Column[datetime]]:
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    ]


def workshop_foreign_key(table_name: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        ["workshop_id"],
        ["workshops.id"],
        name=op.f(f"fk_{table_name}_workshop_id_workshops"),
        ondelete="CASCADE",
    )


def upgrade() -> None:
    op.create_table(
        "workshops",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=220), nullable=False),
        sa.Column("tax_id", sa.String(length=10), nullable=False),
        sa.Column("street", sa.String(length=200), nullable=False),
        sa.Column("postal_code", sa.String(length=6), nullable=False),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        *timestamp_columns(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_workshops")),
        sa.UniqueConstraint("slug", name=op.f("uq_workshops_slug")),
    )
    op.create_index(op.f("ix_workshops_city"), "workshops", ["city"])

    op.create_table(
        "workshop_members",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("workshop_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_workshop_members_user_id_users"),
            ondelete="CASCADE",
        ),
        workshop_foreign_key("workshop_members"),
        sa.PrimaryKeyConstraint("user_id", "workshop_id", name=op.f("pk_workshop_members")),
    )
    op.create_index(
        op.f("ix_workshop_members_workshop_id"),
        "workshop_members",
        ["workshop_id"],
    )

    op.create_table(
        "workshop_opening_hours",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workshop_id", sa.Uuid(), nullable=False),
        sa.Column("weekday", sa.SmallInteger(), nullable=False),
        sa.Column("opens_at", sa.Time(), nullable=False),
        sa.Column("closes_at", sa.Time(), nullable=False),
        workshop_foreign_key("workshop_opening_hours"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_workshop_opening_hours")),
        sa.UniqueConstraint(
            "workshop_id",
            "weekday",
            name=op.f("uq_workshop_opening_hours_workshop_id_weekday"),
        ),
        sa.CheckConstraint(
            "weekday BETWEEN 1 AND 7",
            name=op.f("ck_workshop_opening_hours_weekday_range"),
        ),
        sa.CheckConstraint(
            "closes_at > opens_at",
            name=op.f("ck_workshop_opening_hours_closes_after_opens"),
        ),
    )

    op.create_table(
        "workshop_closures",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workshop_id", sa.Uuid(), nullable=False),
        sa.Column("closed_on", sa.Date(), nullable=False),
        sa.Column("reason", sa.String(length=200), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        workshop_foreign_key("workshop_closures"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_workshop_closures")),
        sa.UniqueConstraint(
            "workshop_id",
            "closed_on",
            name=op.f("uq_workshop_closures_workshop_id_closed_on"),
        ),
    )

    op.create_table(
        "bays",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workshop_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column(
            "type",
            sa.Enum(
                *BAY_TYPES,
                name="bay_type",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        *timestamp_columns(),
        workshop_foreign_key("bays"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_bays")),
        sa.UniqueConstraint("workshop_id", "name", name=op.f("uq_bays_workshop_id_name")),
    )
    op.create_index(op.f("ix_bays_workshop_id"), "bays", ["workshop_id"])

    op.create_table(
        "service_types",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workshop_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("base_price_net", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("vat_rate", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        *timestamp_columns(),
        workshop_foreign_key("service_types"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_service_types")),
        sa.UniqueConstraint(
            "workshop_id",
            "name",
            name=op.f("uq_service_types_workshop_id_name"),
        ),
        sa.CheckConstraint(
            "duration_minutes > 0",
            name=op.f("ck_service_types_duration_positive"),
        ),
        sa.CheckConstraint(
            "base_price_net >= 0",
            name=op.f("ck_service_types_price_not_negative"),
        ),
        sa.CheckConstraint(
            "vat_rate >= 0 AND vat_rate <= 100",
            name=op.f("ck_service_types_vat_rate_range"),
        ),
    )
    op.create_index(op.f("ix_service_types_workshop_id"), "service_types", ["workshop_id"])

    op.create_table(
        "vehicles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("make", sa.String(length=60), nullable=False),
        sa.Column("model", sa.String(length=80), nullable=False),
        sa.Column("production_year", sa.SmallInteger(), nullable=False),
        sa.Column("plate_number", sa.String(length=10), nullable=False),
        sa.Column("vin", sa.String(length=17), nullable=True),
        sa.Column("mileage_km", sa.Integer(), nullable=True),
        sa.Column("engine", sa.String(length=60), nullable=True),
        *timestamp_columns(),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["users.id"],
            name=op.f("fk_vehicles_owner_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_vehicles")),
        sa.CheckConstraint("mileage_km >= 0", name=op.f("ck_vehicles_mileage_not_negative")),
    )
    op.create_index(op.f("ix_vehicles_owner_id"), "vehicles", ["owner_id"])
    op.create_index(op.f("ix_vehicles_plate_number"), "vehicles", ["plate_number"])
    op.create_index(
        "uq_vehicles_vin_active",
        "vehicles",
        ["vin"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL AND vin IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_vehicles_vin_active", table_name="vehicles")
    op.drop_index(op.f("ix_vehicles_plate_number"), table_name="vehicles")
    op.drop_index(op.f("ix_vehicles_owner_id"), table_name="vehicles")
    op.drop_table("vehicles")
    op.drop_index(op.f("ix_service_types_workshop_id"), table_name="service_types")
    op.drop_table("service_types")
    op.drop_index(op.f("ix_bays_workshop_id"), table_name="bays")
    op.drop_table("bays")
    op.drop_table("workshop_closures")
    op.drop_table("workshop_opening_hours")
    op.drop_index(op.f("ix_workshop_members_workshop_id"), table_name="workshop_members")
    op.drop_table("workshop_members")
    op.drop_index(op.f("ix_workshops_city"), table_name="workshops")
    op.drop_table("workshops")
