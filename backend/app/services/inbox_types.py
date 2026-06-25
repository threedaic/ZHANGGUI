"""
收件箱消息类型注册表（Inbox Message Types）

所有会推送到员工收件箱的消息，统一在这里定义类型。
新增类型时只需在 INBOX_TYPES 里加一条，然后调用：

    await inbox_service.send_to_inbox(
        employee_id=...,
        msg_type=InboxType.SALARY_SLIP,
        ref_id=...,
        issued_by=...,
        extra={...},
    )

标题、ref_type 等由注册表自动填充，不用每次手写。
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class InboxTypeMeta:
    """单个收件箱类型的元数据"""
    code: str               # 类型代码（存数据库 type 字段）
    label: str              # 中文显示名
    ref_type: str           # 关联业务表类型
    title_template: str     # 标题模板，{placeholder} 会被 extra 里同名字段替换
    icon: str               # 前端图标标识（前端按此选图标）
    color: str              # 前端卡片颜色标识


class InboxType:
    """收件箱消息类型枚举"""

    # 工资单 —— 账期锁定后会计发送
    SALARY_SLIP = "salary_slip"

    # 考勤确认单 —— 考勤锁定后发送，员工签收
    ATTENDANCE_CONFIRM = "attendance_confirm"

    # 处罚通知 —— 开罚单时发送
    PENALTY_NOTICE = "penalty_notice"


# ====== 类型注册表（唯一真相源） ======
INBOX_TYPES: dict[str, InboxTypeMeta] = {
    InboxType.SALARY_SLIP: InboxTypeMeta(
        code="salary_slip",
        label="工资单",
        ref_type="wage_record",
        title_template="{period}年工资单 - {employee_name}",
        icon="money",
        color="#FB0079",
    ),
    InboxType.ATTENDANCE_CONFIRM: InboxTypeMeta(
        code="attendance_confirm",
        label="考勤确认单",
        ref_type="attendance",
        title_template="{period}考勤确认单 - {employee_name}",
        icon="calendar",
        color="#3B82F6",
    ),
    InboxType.PENALTY_NOTICE: InboxTypeMeta(
        code="penalty_notice",
        label="处罚通知",
        ref_type="penalty_notice",
        title_template="{category}通知 - {penalty_label}",
        icon="warning",
        color="#EF4444",
    ),
}


def get_inbox_type(code: str) -> InboxTypeMeta | None:
    """查类型元数据，不存在返回 None"""
    return INBOX_TYPES.get(code)
