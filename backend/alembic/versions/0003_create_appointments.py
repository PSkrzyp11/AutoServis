from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

BAY_TYPES = ("GENERAL", "LIFT", "DIAGNOSTIC", "TIRES")
APPOINTMENT_STATUSES = ("SCHEDULED", "CHECKED_IN", "CANCELLED", "NO_SHOW")
ACTIVE_STATUS_CONDITION = "status IN ('SCHEDULED', 'CHECKED_IN')"
PERIOD_EXPRESSION = "tstzrange(start_at, end_at, '[)')"


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")

    op.add_column(
        "service_types",
        sa.Column(
            "required_bay_type",
            sa.Enum(
                *BAY_TYPES,
                name="required_bay_type",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=True,
        ),
    )

    op.create_table(
        "appointments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workshop_id", sa.Uuid(), nullable=False),
        sa.Column("bay_id", sa.Uuid(), nullable=False),
        sa.Column("vehicle_id", sa.Uuid(), nullable=False),
        sa.Column("client_id", sa.Uuid(), nullable=False),
        sa.Column("service_type_id", sa.Uuid(), nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "period",
            postgresql.TSTZRANGE(),
            sa.Computed(PERIOD_EXPRESSION, persisted=True),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                *APPOINTMENT_STATUSES,
                name="appointment_status",
                native_enum=False,
                create_constraint=True,
                length=32,
            ),
            nullable=False,
        ),
        sa.Column("problem_description", sa.Text(), nullable=True),
        sa.Column("reminder_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["workshop_id"],
            ["workshops.id"],
            name=op.f("fk_appointments_workshop_id_workshops"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["bay_id"],
            ["bays.id"],
            name=op.f("fk_appointments_bay_id_bays"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["vehicle_id"],
            ["vehicles.id"],
            name=op.f("fk_appointments_vehicle_id_vehicles"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["client_id"],
            ["users.id"],
            name=op.f("fk_appointments_client_id_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["service_type_id"],
            ["service_types.id"],
            name=op.f("fk_appointments_service_type_id_service_types"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_appointments")),
        sa.CheckConstraint("end_at > start_at", name=op.f("ck_appointments_ends_after_start")),
        postgresql.ExcludeConstraint(
            ("bay_id", "="),
            ("period", "&&"),
            using="gist",
            where=sa.text(ACTIVE_STATUS_CONDITION),
            name="ex_appointments_bay_id_period",
        ),
        postgresql.ExcludeConstraint(
            ("vehicle_id", "="),
            ("period", "&&"),
            using="gist",
            where=sa.text(ACTIVE_STATUS_CONDITION),
            name="ex_appointments_vehicle_id_period",
        ),
    )
    op.create_index(op.f("ix_appointments_client_id"), "appointments", ["client_id"])
    op.create_index(
        "ix_appointments_workshop_id_start_at",
        "appointments",
        ["workshop_id", "start_at"],
    )
    op.create_index("ix_appointments_status_start_at", "appointments", ["status", "start_at"])


def downgrade() -> None:
    op.drop_index("ix_appointments_status_start_at", table_name="appointments")
    op.drop_index("ix_appointments_workshop_id_start_at", table_name="appointments")
    op.drop_index(op.f("ix_appointments_client_id"), table_name="appointments")
    op.drop_table("appointments")
    op.drop_column("service_types", "required_bay_type")
    op.execute("DROP EXTENSION IF EXISTS btree_gist")
