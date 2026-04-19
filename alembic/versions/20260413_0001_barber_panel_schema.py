"""barber panel schema

Revision ID: 20260413_0001
Revises:
Create Date: 2026-04-13
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260413_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bp_barbers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("telegram_id", sa.Integer(), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("salon_name", sa.String(length=255), nullable=False),
        sa.Column("phone_number", sa.String(length=32), nullable=False),
        sa.Column("address", sa.String(length=255), nullable=False),
        sa.Column("experience", sa.String(length=120), nullable=False),
        sa.Column("about_me", sa.Text(), nullable=False),
        sa.Column("profile_image_file_id", sa.String(length=255), nullable=True),
        sa.Column("theme", sa.String(length=32), nullable=False),
        sa.Column("notifications_enabled", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_bp_barbers")),
        sa.UniqueConstraint("telegram_id", name=op.f("uq_bp_barbers_telegram_id")),
    )
    op.create_index(op.f("ix_bp_barbers_telegram_id"), "bp_barbers", ["telegram_id"], unique=False)

    op.create_table(
        "bp_services",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("barber_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("price", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["barber_id"], ["bp_barbers.id"], name=op.f("fk_bp_services_barber_id_bp_barbers"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_bp_services")),
        sa.UniqueConstraint("barber_id", "name", name=op.f("uq_bp_services_barber_id")),
    )

    op.create_table(
        "bp_schedules",
        sa.Column("barber_id", sa.Integer(), nullable=False),
        sa.Column("working_days", sa.JSON(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("break_start", sa.Time(), nullable=True),
        sa.Column("break_end", sa.Time(), nullable=True),
        sa.Column("unavailable_dates", sa.JSON(), nullable=False),
        sa.Column("custom_open_slots", sa.JSON(), nullable=False),
        sa.Column("custom_closed_slots", sa.JSON(), nullable=False),
        sa.Column("vacation_mode", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["barber_id"], ["bp_barbers.id"], name=op.f("fk_bp_schedules_barber_id_bp_barbers"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("barber_id", name=op.f("pk_bp_schedules")),
    )

    op.create_table(
        "bp_portfolio_images",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("barber_id", sa.Integer(), nullable=False),
        sa.Column("telegram_file_id", sa.String(length=255), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["barber_id"], ["bp_barbers.id"], name=op.f("fk_bp_portfolio_images_barber_id_bp_barbers"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_bp_portfolio_images")),
    )

    op.create_table(
        "bp_bookings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("barber_id", sa.Integer(), nullable=False),
        sa.Column("service_id", sa.Integer(), nullable=False),
        sa.Column("client_name", sa.String(length=255), nullable=False),
        sa.Column("client_phone", sa.String(length=32), nullable=False),
        sa.Column("client_telegram_id", sa.Integer(), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.Enum("pending", "accepted", "completed", "cancelled", name="bookingstatus", native_enum=False), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["barber_id"], ["bp_barbers.id"], name=op.f("fk_bp_bookings_barber_id_bp_barbers"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["service_id"], ["bp_services.id"], name=op.f("fk_bp_bookings_service_id_bp_services"), ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_bp_bookings")),
    )
    op.create_index(op.f("ix_bp_bookings_scheduled_at"), "bp_bookings", ["scheduled_at"], unique=False)

    op.create_table(
        "bp_reviews",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("barber_id", sa.Integer(), nullable=False),
        sa.Column("booking_id", sa.Integer(), nullable=True),
        sa.Column("client_name", sa.String(length=255), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=False),
        sa.Column("is_verified", sa.Boolean(), nullable=False),
        sa.Column("reply_text", sa.Text(), nullable=True),
        sa.Column("replied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["barber_id"], ["bp_barbers.id"], name=op.f("fk_bp_reviews_barber_id_bp_barbers"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["booking_id"], ["bp_bookings.id"], name=op.f("fk_bp_reviews_booking_id_bp_bookings"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_bp_reviews")),
    )

    op.create_table(
        "bp_chat_threads",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("barber_id", sa.Integer(), nullable=False),
        sa.Column("booking_id", sa.Integer(), nullable=True),
        sa.Column("client_name", sa.String(length=255), nullable=False),
        sa.Column("client_telegram_id", sa.Integer(), nullable=True),
        sa.Column("last_message_preview", sa.String(length=255), nullable=False),
        sa.Column("unread_count", sa.Integer(), nullable=False),
        sa.Column("booking_related", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["barber_id"], ["bp_barbers.id"], name=op.f("fk_bp_chat_threads_barber_id_bp_barbers"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["booking_id"], ["bp_bookings.id"], name=op.f("fk_bp_chat_threads_booking_id_bp_bookings"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_bp_chat_threads")),
    )

    op.create_table(
        "bp_chat_messages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("thread_id", sa.Integer(), nullable=False),
        sa.Column("direction", sa.Enum("inbound", "outbound", name="chatmessagedirection", native_enum=False), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["thread_id"], ["bp_chat_threads.id"], name=op.f("fk_bp_chat_messages_thread_id_bp_chat_threads"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_bp_chat_messages")),
    )


def downgrade() -> None:
    op.drop_table("bp_chat_messages")
    op.drop_table("bp_chat_threads")
    op.drop_table("bp_reviews")
    op.drop_index(op.f("ix_bp_bookings_scheduled_at"), table_name="bp_bookings")
    op.drop_table("bp_bookings")
    op.drop_table("bp_portfolio_images")
    op.drop_table("bp_schedules")
    op.drop_table("bp_services")
    op.drop_index(op.f("ix_bp_barbers_telegram_id"), table_name="bp_barbers")
    op.drop_table("bp_barbers")
