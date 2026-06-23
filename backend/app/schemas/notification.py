"""
消息通知 Pydantic 模型
"""
import uuid
from pydantic import BaseModel


class NotificationItem(BaseModel):
    id: uuid.UUID
    type: str
    title: str
    content: str
    channel: str
    is_read: bool
    created_at: str | None = None


class NotificationSettingItem(BaseModel):
    id: uuid.UUID
    setting_key: str
    enabled: bool
    channel: str
    push_to_group: bool = False
    target_roles: list[str]
    schedule_time: str | None = None


class NotificationSettingSaveRequest(BaseModel):
    setting_key: str
    enabled: bool
    channel: str
    push_to_group: bool = False
    target_roles: list[str]
    schedule_time: str | None = None
