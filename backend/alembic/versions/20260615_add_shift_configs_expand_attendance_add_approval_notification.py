"""add shift_configs expand attendance add approval notification

Revision ID: 20260615
Revises:
Create Date: 2026-06-15 23:30:00
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260615"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. 扩展 attendance_records 表
    op.add_column(
        "attendance_records",
        sa.Column("shift_start_time", sa.String(length=8), nullable=True),
    )
    op.add_column(
        "attendance_records",
        sa.Column("shift_end_time", sa.String(length=8), nullable=True),
    )
    op.add_column(
        "attendance_records",
        sa.Column("is_overnight", sa.Boolean(), nullable=False, server_default="false"),
    )

    # 2. 新建 shift_configs 表
    op.create_table(
        "shift_configs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("store_id", sa.Integer(), sa.ForeignKey("stores.id"), nullable=False),
        sa.Column("shift_code", sa.String(length=20), nullable=False),
        sa.Column("shift_name", sa.String(length=20), nullable=False),
        sa.Column("start_time", sa.String(length=8), nullable=False),
        sa.Column("end_time", sa.String(length=8), nullable=False),
        sa.Column("is_overnight", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("color", sa.String(length=8), nullable=False, server_default="#FB0079"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("store_id", "shift_code"),
    )

    # 3. 新建 approval_requests 表
    op.create_table(
        "approval_requests",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("store_id", sa.Integer(), sa.ForeignKey("stores.id"), nullable=False),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id"), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("extra", sa.JSON(), nullable=True),
        sa.Column("approver_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # 4. 新建 notifications 表
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("store_id", sa.Integer(), sa.ForeignKey("stores.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("type", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("channel", sa.String(length=20), nullable=False, server_default="in_app"),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("extra", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # 5. 新建 notification_settings 表
    op.create_table(
        "notification_settings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("store_id", sa.Integer(), sa.ForeignKey("stores.id"), nullable=False),
        sa.Column("setting_key", sa.String(length=40), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("channel", sa.String(length=20), nullable=False, server_default="all"),
        sa.Column("target_roles", sa.JSON(), nullable=False, server_default='["boss", "store_manager"]'),
        sa.Column("schedule_time", sa.String(length=8), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("store_id", "setting_key"),
    )

    # 6. 初始化默认班次配置（对 store_id=1）
    op.execute(
        """
        INSERT INTO shift_configs (store_id, shift_code, shift_name, start_time, end_time, is_overnight, color, sort_order)
        VALUES
            (1, 'day', '白班', '12:00', '20:00', false, '#FB0079', 1),
            (1, 'night', '晚班', '19:00', '03:00', true, '#333333', 2)
        ON CONFLICT (store_id, shift_code) DO NOTHING;
        """
    )

    # 7. 初始化默认推送设置
    op.execute(
        """
        INSERT INTO notification_settings (store_id, setting_key, enabled, channel, target_roles, schedule_time)
        VALUES
            (1, 'daily_report', true, 'all', '["boss", "store_manager"]', '23:00'),
            (1, 'attendance_alert', true, 'all', '["boss", "store_manager"]', null),
            (1, 'shift_change', true, 'all', '["staff"]', null),
            (1, 'approval', true, 'all', '["boss", "store_manager", "staff"]', null),
            (1, 'reminder', false, 'all', '["staff"]', null)
        ON CONFLICT (store_id, setting_key) DO NOTHING;
        """
    )


def downgrade() -> None:
    op.drop_table("notification_settings")
    op.drop_table("notifications")
    op.drop_table("approval_requests")
    op.drop_table("shift_configs")
    op.drop_column("attendance_records", "shift_start_time")
    op.drop_column("attendance_records", "shift_end_time")
    op.drop_column("attendance_records", "is_overnight")
