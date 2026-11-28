from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ORDER_STATUSES = (
    "RECEIVED",
    "DIAGNOSIS",
    "WAITING_FOR_APPROVAL",
    "WAITING_FOR_PARTS",
    "IN_PROGRESS",
    "READY",
    "COMPLETED",
    "CANCELLED",
)
NOTIFICATION_TYPES = ("ORDER_STATUS_CHANGED", "ORDER_ASSIGNED")
ENUM_LENGTH = 32


def string_enum(values: Sequence[str], name: str) -> sa.Enum:
    return sa.Enum(
        *values,
        name=name,
        native_enum=False,
        create_constraint=True,
        length=ENUM_LENGTH,
    )


def timestamp_column(name: str) -> sa.Column[object]:
    return sa.Column(
        name,
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),
        nullable=False,
    )


def upgrade() -> None:
    op.create_table(
        "service_orders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("number", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("workshop_id", sa.Uuid(), nullable=False),
        sa.Column("appointment_id", sa.Uuid(), nullable=False),
        sa.Column("mechanic_id", sa.Uuid(), nullable=True),
        sa.Column("status", string_enum(ORDER_STATUSES, "order_status"), nullable=False),
        sa.Column("diagnosis", sa.Text(), nullable=True),
        timestamp_column("status_changed_at"),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        timestamp_column("created_at"),
        timestamp_column("updated_at"),
        sa.ForeignKeyConstraint(
            ["workshop_id"],
            ["workshops.id"],
            name=op.f("fk_service_orders_workshop_id_workshops"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["appointment_id"],
            ["appointments.id"],
            name=op.f("fk_service_orders_appointment_id_appointments"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["mechanic_id"],
            ["users.id"],
            name=op.f("fk_service_orders_mechanic_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_service_orders")),
        sa.UniqueConstraint("number", name=op.f("uq_service_orders_number")),
        sa.UniqueConstraint("appointment_id", name=op.f("uq_service_orders_appointment_id")),
    )
    op.create_index(
        "ix_service_orders_workshop_id_status",
        "service_orders",
        ["workshop_id", "status"],
    )
    op.create_index("ix_service_orders_mechanic_id", "service_orders", ["mechanic_id"])

    op.create_table(
        "order_status_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column(
            "from_status",
            string_enum(ORDER_STATUSES, "order_history_from_status"),
            nullable=True,
        ),
        sa.Column(
            "to_status",
            string_enum(ORDER_STATUSES, "order_history_to_status"),
            nullable=False,
        ),
        sa.Column("changed_by_id", sa.Uuid(), nullable=True),
        sa.Column("note", sa.String(length=500), nullable=True),
        timestamp_column("changed_at"),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["service_orders.id"],
            name=op.f("fk_order_status_history_order_id_service_orders"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["changed_by_id"],
            ["users.id"],
            name=op.f("fk_order_status_history_changed_by_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_order_status_history")),
    )
    op.create_index(
        "ix_order_status_history_order_id_changed_at",
        "order_status_history",
        ["order_id", "changed_at"],
    )

    op.create_table(
        "notifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("type", string_enum(NOTIFICATION_TYPES, "notification_type"), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        timestamp_column("created_at"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_notifications_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_notifications")),
    )
    op.create_index(
        "ix_notifications_user_id_created_at",
        "notifications",
        ["user_id", "created_at"],
    )
    op.create_index(
        "ix_notifications_user_id_unread",
        "notifications",
        ["user_id"],
        postgresql_where=sa.text("read_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_notifications_user_id_unread", table_name="notifications")
    op.drop_index("ix_notifications_user_id_created_at", table_name="notifications")
    op.drop_table("notifications")
    op.drop_index(
        "ix_order_status_history_order_id_changed_at",
        table_name="order_status_history",
    )
    op.drop_table("order_status_history")
    op.drop_index("ix_service_orders_mechanic_id", table_name="service_orders")
    op.drop_index("ix_service_orders_workshop_id_status", table_name="service_orders")
    op.drop_table("service_orders")
