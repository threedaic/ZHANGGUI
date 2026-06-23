"""Crush 2.0 Schema 迁移：26张表 + RLS策略

Revision ID: crush_2_0_schema
Revises: 20260615_add_shift_configs_expand_attendance_add_approval_notification
Create Date: 2026-06-22

依据 SPEC 2.0 第三章，创建 shared_*/pos_*/game_*/sys_* 共26张表，
启用 RLS 策略（session 变量方式）。
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "crush_2_0_schema"
down_revision = "20260615"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 直接执行完整建表 SQL（含 RLS 策略、索引、触发器）
    sql_file = "20260622_crush_2_0_schema.sql"
    import os
    here = os.path.dirname(__file__)
    sql_path = os.path.join(here, sql_file)
    with open(sql_path, "r", encoding="utf-8") as f:
        sql_text = f.read()
    # 按分号切分执行（保留函数体）
    op.execute(sql_text)


def downgrade() -> None:
    # 按依赖反序删除
    tables = [
        "sys_printers",
        "sys_audit_logs",
        "sys_configs",
        "game_prizes",
        "game_participants",
        "game_sessions",
        "game_templates",
        "pos_desk_notes",
        "pos_daily_reconciliations",
        "pos_order_logs",
        "pos_member_transactions",
        "pos_discount_approvals",
        "pos_refunds",
        "pos_table_sessions",
        "pos_payment_methods",
        "pos_payments",
        "pos_order_items",
        "pos_orders",
        "shared_store_settings",
        "shared_devices",
        "shared_tables",
        "shared_products",
        "shared_categories",
        "shared_member_levels",
        "shared_members",
        "shared_employees",
        "shared_franchisees",
        "shared_stores",
    ]
    for t in tables:
        op.execute(f'DROP TABLE IF EXISTS "{t}" CASCADE;')
