"""
工资公式引擎

解析公式 AST（JSON）并从各数据源取数计算工资项金额。

公式 AST 节点类型:
  - {"type": "const", "value": 0.10}                    常量
  - {"type": "field", "source": "contract", "field": "monthly_salary"}  数据源字段
  - {"type": "op", "op": "+|-|*|/", "left": {...}, "right": {...}}  运算
  - {"type": "func", "name": "max|min|round|if", "args": [...]}  函数

数据源(context):
  - contract:     {"monthly_salary", "base_salary", "meal_allowance", "allowance"}
  - attendance:   {"late_count", "total_late_minutes", "absent_count", "early_count", "present_days", "total_days"}
  - performance:  {"total_amount", "booking", "wework_payment", "bottle", "card"}
  - kpi:          {"coefficient", "total_score"}
  - rule:         {"late_deduction_per_minute", "absent_factor", "early_deduction_per_time", "commission_rate", "rest_days_per_month", ...}
  - manual:       手工录入值（生成工资时由店长填写）
"""
from typing import Any
from loguru import logger
from app.utils.exceptions import ValidationError


class FormulaEngine:
    """公式引擎：解析 AST 并计算结果"""

    # 支持的运算符
    OPERATORS = {"+", "-", "*", "/"}

    # 支持的函数
    FUNCTIONS = {"max", "min", "round", "abs", "if"}

    def evaluate(self, ast: dict | None, context: dict[str, Any]) -> tuple[float, dict]:
        """计算公式 AST

        Args:
            ast: 公式抽象语法树（JSON）
            context: 数据源上下文 {source: {field: value}}

        Returns:
            (计算结果, 计算明细)
            计算明细用于审计追溯，如 {"formula": "迟到分钟×5", "inputs": {...}, "result": 50.0}
        """
        if ast is None:
            return 0.0, {"reason": "公式为空，返回0"}

        try:
            result = self._eval_node(ast, context)
            detail = {
                "formula": self._ast_to_string(ast),
                "result": round(float(result), 2),
            }
            return round(float(result), 2), detail
        except Exception as e:
            logger.warning(f"[FormulaEngine] 公式计算失败: {e}, ast={ast}")
            raise ValidationError(f"公式计算失败: {e}")

    def _eval_node(self, node: dict, context: dict[str, Any]) -> float:
        """递归计算 AST 节点"""
        if not isinstance(node, dict):
            raise ValidationError(f"AST 节点必须是 dict，实际: {type(node)}")

        node_type = node.get("type")
        if node_type == "const":
            return float(node.get("value", 0))

        elif node_type == "field":
            return self._eval_field(node, context)

        elif node_type == "op":
            return self._eval_op(node, context)

        elif node_type == "func":
            return self._eval_func(node, context)

        else:
            raise ValidationError(f"未知的 AST 节点类型: {node_type}")

    def _eval_field(self, node: dict, context: dict[str, Any]) -> float:
        """取数据源字段值"""
        source = node.get("source")
        field = node.get("field")
        if not source or not field:
            raise ValidationError(f"field 节点缺少 source/field: {node}")

        source_data = context.get(source, {})
        if not isinstance(source_data, dict):
            raise ValidationError(f"数据源 {source} 不是 dict: {source_data}")

        value = source_data.get(field)
        if value is None:
            return 0.0
        return float(value)

    def _eval_op(self, node: dict, context: dict[str, Any]) -> float:
        """运算符节点"""
        op = node.get("op")
        if op not in self.OPERATORS:
            raise ValidationError(f"不支持的运算符: {op}")

        left = self._eval_node(node.get("left", {}), context)
        right = self._eval_node(node.get("right", {}), context)

        if op == "+":
            return left + right
        elif op == "-":
            return left - right
        elif op == "*":
            return left * right
        elif op == "/":
            if right == 0:
                raise ValidationError("除数为0")
            return left / right
        return 0.0

    def _eval_func(self, node: dict, context: dict[str, Any]) -> float:
        """函数节点"""
        name = node.get("name")
        if name not in self.FUNCTIONS:
            raise ValidationError(f"不支持的函数: {name}")

        args = [self._eval_node(arg, context) for arg in node.get("args", [])]

        if name == "max":
            return max(args) if args else 0.0
        elif name == "min":
            return min(args) if args else 0.0
        elif name == "round":
            if len(args) < 1:
                return 0.0
            digits = int(args[1]) if len(args) > 1 else 2
            return round(args[0], digits)
        elif name == "abs":
            return abs(args[0]) if args else 0.0
        elif name == "if":
            # if(cond, true_val, false_val)
            if len(args) < 3:
                raise ValidationError("if 函数需要 3 个参数")
            return args[1] if args[0] > 0 else args[2]
        return 0.0

    def _ast_to_string(self, node: dict) -> str:
        """将 AST 转为可读字符串（用于审计）"""
        try:
            if not isinstance(node, dict):
                return str(node)
            node_type = node.get("type")
            if node_type == "const":
                return str(node.get("value", 0))
            elif node_type == "field":
                return f"{node.get('source')}.{node.get('field')}"
            elif node_type == "op":
                left = self._ast_to_string(node.get("left", {}))
                right = self._ast_to_string(node.get("right", {}))
                return f"({left} {node.get('op')} {right})"
            elif node_type == "func":
                args = ", ".join(
                    self._ast_to_string(arg) for arg in node.get("args", [])
                )
                return f"{node.get('name')}({args})"
            return str(node)
        except Exception:
            return str(node)


# ==================== 内置公式模板 ====================

BUILTIN_FORMULAS = {
    # 底薪 = 合同月薪
    "base_salary": {
        "type": "field",
        "source": "contract",
        "field": "monthly_salary",
    },
    # 餐补 = 合同餐补
    "meal_allowance": {
        "type": "field",
        "source": "contract",
        "field": "meal_allowance",
    },
    # 提成 = 个人业绩总额 × 提成比例
    "commission": {
        "type": "op",
        "op": "*",
        "left": {"type": "field", "source": "performance", "field": "total_amount"},
        "right": {"type": "field", "source": "rule", "field": "commission_rate"},
    },
    # KPI奖金 = 底薪 × (KPI系数 - 1)
    "kpi_bonus": {
        "type": "op",
        "op": "*",
        "left": {"type": "field", "source": "contract", "field": "monthly_salary"},
        "right": {
            "type": "op",
            "op": "-",
            "left": {"type": "field", "source": "kpi", "field": "coefficient"},
            "right": {"type": "const", "value": 1.0},
        },
    },
    # 迟到扣款 = 迟到分钟 × 每分钟扣款
    "deduction_late": {
        "type": "op",
        "op": "*",
        "left": {"type": "field", "source": "attendance", "field": "total_late_minutes"},
        "right": {"type": "field", "source": "rule", "field": "late_deduction_per_minute"},
    },
    # 旷工扣款 = 旷工天数 × 日薪 × 旷工倍数
    # 日薪 = 月薪 / (当月天数 - 休息天数)
    "deduction_absent": {
        "type": "op",
        "op": "*",
        "left": {"type": "field", "source": "attendance", "field": "absent_count"},
        "right": {
            "type": "op",
            "op": "*",
            "left": {
                "type": "op",
                "op": "/",
                "left": {"type": "field", "source": "contract", "field": "monthly_salary"},
                "right": {
                    "type": "op",
                    "op": "-",
                    "left": {"type": "const", "value": 30},  # 当月天数（简化）
                    "right": {"type": "field", "source": "rule", "field": "rest_days_per_month"},
                },
            },
            "right": {"type": "field", "source": "rule", "field": "absent_factor"},
        },
    },
    # 早退扣款 = 早退次数 × 每次扣款
    "deduction_early": {
        "type": "op",
        "op": "*",
        "left": {"type": "field", "source": "attendance", "field": "early_count"},
        "right": {"type": "field", "source": "rule", "field": "early_deduction_per_time"},
    },
}
