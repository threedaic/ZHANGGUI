"""
合同系统业务逻辑

- 薪资矩阵：5岗位 x 4档
- 签约流程：选人 -> 填月薪 -> 自动算补贴 = 月薪 - 3000
- 腾讯电子签：占位，对接 API 时替换 TODO 标记
- 模板自动填充 20+ 字段
"""
from datetime import date, datetime
from typing import Optional
from loguru import logger
from app.models.contract import Contract
from app.repositories.contract import ContractRepository
from app.utils.exceptions import NotFoundError, ValidationError, ConflictError
from app.utils.http_client import http_client

# ---- 薪资矩阵常量（5岗 x 4档）----

SALARY_MATRIX_SEED: list[dict] = [
    # 店长
    {"position": "店长", "grade": "学徒", "monthly_salary": 0, "base_salary": 3000, "meal_allowance": 400, "is_active": False},
    {"position": "店长", "grade": "正式", "monthly_salary": 11000, "base_salary": 3000, "meal_allowance": 400},
    {"position": "店长", "grade": "副职", "monthly_salary": 0, "base_salary": 3000, "meal_allowance": 400, "is_active": False},
    {"position": "店长", "grade": "正职", "monthly_salary": 12000, "base_salary": 3000, "meal_allowance": 400},
    # 吧员
    {"position": "吧员", "grade": "学徒", "monthly_salary": 5000, "base_salary": 3000, "meal_allowance": 400},
    {"position": "吧员", "grade": "正式", "monthly_salary": 6000, "base_salary": 3000, "meal_allowance": 400},
    {"position": "吧员", "grade": "副职", "monthly_salary": 7000, "base_salary": 3000, "meal_allowance": 400},
    {"position": "吧员", "grade": "正职", "monthly_salary": 9000, "base_salary": 3000, "meal_allowance": 400},
    # 服务员
    {"position": "服务员", "grade": "学徒", "monthly_salary": 5000, "base_salary": 3000, "meal_allowance": 400},
    {"position": "服务员", "grade": "正式", "monthly_salary": 6000, "base_salary": 3000, "meal_allowance": 400},
    {"position": "服务员", "grade": "副职", "monthly_salary": 7000, "base_salary": 3000, "meal_allowance": 400},
    {"position": "服务员", "grade": "正职", "monthly_salary": 8000, "base_salary": 3000, "meal_allowance": 400},
    # 厨师
    {"position": "厨师", "grade": "学徒", "monthly_salary": 5000, "base_salary": 3000, "meal_allowance": 400},
    {"position": "厨师", "grade": "正式", "monthly_salary": 6000, "base_salary": 3000, "meal_allowance": 400},
    {"position": "厨师", "grade": "副职", "monthly_salary": 7000, "base_salary": 3000, "meal_allowance": 400},
    {"position": "厨师", "grade": "正职", "monthly_salary": 8000, "base_salary": 3000, "meal_allowance": 400},
    # 保洁
    {"position": "保洁", "grade": "学徒", "monthly_salary": 0, "base_salary": 3000, "meal_allowance": 400, "is_active": False},
    {"position": "保洁", "grade": "正式", "monthly_salary": 6000, "base_salary": 3000, "meal_allowance": 400},
    {"position": "保洁", "grade": "副职", "monthly_salary": 0, "base_salary": 3000, "meal_allowance": 400, "is_active": False},
    {"position": "保洁", "grade": "正职", "monthly_salary": 0, "base_salary": 3000, "meal_allowance": 400, "is_active": False},
]

# 工资公式
BASE_SALARY = 3000.0
MEAL_ALLOWANCE = 400.0


async def seed_salary_matrix(repo: ContractRepository):
    """首次启动时，若薪资矩阵为空则写入默认值。"""
    existing = await repo.list_salary_matrix()
    if existing:
        return

    from app.models.contract import SalaryMatrix
    for item in SALARY_MATRIX_SEED:
        entry = SalaryMatrix(**item)
        repo.session.add(entry)
    await repo.session.flush()
    logger.info("薪资矩阵种子数据已写入")


# ---- 核心计算 ----

def compute_allowance(monthly_salary: float) -> float:
    """补贴 = 月薪 - 基本工资 - 餐补

    月薪总额已包含基本工资(3000) + 餐补(400) + 补贴。
    例: 7000 = 3000 + 400 + 3600(补贴)
    """
    return max(0.0, monthly_salary - BASE_SALARY - MEAL_ALLOWANCE)


def generate_contract_no(store_id: int, employee_id: int, seq: int) -> str:
    """生成合同编号: CT-{store_id}-{employee_id}-{seq:04d}"""
    return f"CT-{store_id}-{employee_id}-{seq:04d}"


# ---- 模板填充（20+ 字段）----

def build_template_data(
    contract: Contract,
    employee_name: str,
    employee_phone: str,
    employee_id_card: str = "",
    company_name: str = "北京跨时餐饮有限公司",  # 应从 StoreSettings 读取，默认值仅用于兜底
    company_address: str = "北京市朝阳区工人体育场北路4号80号楼一层113室",  # 应从 StoreSettings 读取，默认值仅用于兜底
    legal_rep: str = "",
    unified_social_credit_code: str = "91110105MADYP9JH2X",  # 应从 StoreSettings 读取，默认值仅用于兜底
    store_name: str = "",  # 应从 StoreSettings 读取，默认值仅用于兜底
) -> dict:
    """构建合同模板填充数据（20+ 字段）。

    字段映射到 Crush劳务合同标准版（2025）主合同 + 5附件。
    附件3（一次性生活补助）+ 附件5（岗位绩效）合并为「补贴」展示。

    公司主体信息应优先从 StoreSettings 读取，此处默认值仅用于冷启动兜底。
    """
    return {
        # === 主合同信息 ===
        "contract_no": contract.contract_no,
        "sign_date": str(date.today()),
        # === 甲方（公司）===
        "company_name": company_name,
        "company_address": company_address,
        "legal_representative": legal_rep,
        "unified_social_credit_code": "91110105MADYP9JH2X",
        # === 乙方（员工）===
        "employee_name": employee_name,
        "employee_phone": employee_phone,
        "employee_id_card": employee_id_card,
        "employee_address": "",
        "employee_bank_account": "",
        "employee_bank_name": "",
        # === 岗位信息 ===
        "position": contract.position,
        "grade": contract.grade,
        "store_name": store_name,
        # === 薪资信息（合同工资公式）===
        "monthly_salary": contract.monthly_salary,
        "base_salary": contract.base_salary,
        "allowance": contract.allowance,  # 附件3 一次性生活补助 + 附件5 岗位绩效 合并
        "meal_allowance": contract.meal_allowance,
        # === 合同期限 ===
        "start_date": str(contract.start_date),
        "end_date": str(contract.end_date) if contract.end_date else "",
        "probation_months": 1,
        # === 工作制度 ===
        "working_hours_system": "综合计算工时工作制",
        "rest_day": "排班轮休",
        # === 附加信息 ===
        "attachment_count": 5,
        "attachment_names": [
            "附件1 岗位职责说明书",
            "附件2 薪酬确认书",
            "附件3 一次性生活补助协议",
            "附件4 竞业限制与保密协议",
            "附件5 岗位绩效协议",
        ],
    }


# ---- 腾讯电子签（占位）----

async def send_for_esign(
    contract: Contract,
    repo: ContractRepository,
) -> dict:
    """发起腾讯电子签签署流程。

    当前为占位实现，返回模拟结果。
    TODO: 对接腾讯电子签 API
    - CreateFlow: 创建签署流程
    - CreateDocument: 填充模板 PDF
    - StartFlow: 发起签署
    - 回调: /api/v1/contracts/esign-callback 更新状态
    """
    template_data = contract.template_data or {}

    # TODO: 替换为真实腾讯电子签 API 调用
    # 占位：模拟生成 flow_id
    fake_flow_id = f"esign_{contract.id}_{contract.employee_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    logger.info(
        f"[电子签-占位] 合同 #{contract.id} ({contract.contract_no}) "
        f"发起签署，模拟 flow_id={fake_flow_id}"
    )

    # 更新合同状态
    await repo.update(
        contract,
        status="pending_sign",
        esign_flow_id=fake_flow_id,
    )

    return {
        "flow_id": fake_flow_id,
        "status": "pending_sign",
        "message": "电子签流程已发起（占位），员工将在企微中收到签署链接",
    }
