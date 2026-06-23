# Crush 掌柜 2.0

> 连锁餐饮门店一体化管理系统 —— 自动算工资、员工排名激励、数据隐私管控

## 📖 项目简介

Crush 掌柜 2.0 是面向连锁餐饮企业的一体化管理平台，核心目标是**通过数据闭环实现自动算工资**，并支持多维度员工排名激励。系统采用多角色权限模型（老板/店长/员工），保障工资数据隐私的同时，打通订座、考勤、业绩、KPI 全链路。

## 🛠️ 技术栈

### 后端
- **框架**：FastAPI (Python 3.12)
- **数据库**：PostgreSQL 16（启用行级安全 RLS）
- **缓存**：Redis 7
- **认证**：企业微信 OAuth + JWT
- **部署**：Docker Compose

### 前端
- **框架**：Vue 3 + TypeScript
- **构建**：Vite
- **状态管理**：Pinia
- **UI 组件**：Vant（移动端）+ Element Plus（管理端）
- **样式**：SCSS

## ✨ 核心功能

| 模块 | 说明 |
|---|---|
| 🧮 **自动算工资** | 可视化公式编辑器，基于合同+考勤+业绩+KPI 自动计算 |
| 📊 **4 维排名** | 业绩排名 / KPI 排名 / 考勤排名 / 评分排名 |
| 🔒 **数据隐私** | 工资数据仅本人/店长/老板可见，排名页脱敏展示 |
| 📅 **账期管理** | open → locked → closed 状态流，关账后不可修改 |
| ⏰ **考勤排班** | 班次配置、排班、换班申请、假期余额 |
| 📋 **KPI 考核** | 模板配置、评分、结果、申诉全流程 |
| 🍷 **酒水盘点** | 库存管理、盘点单、差异分析 |
| 🏪 **多门店** | 通过企微部门区分连锁店，统一管理 |

## 📁 项目结构

```
crush-zhanggui/
├── backend/                 # 后端 FastAPI
│   ├── app/
│   │   ├── api/v1/         # API 路由（24 个模块）
│   │   ├── models/         # 数据模型（44 张表）
│   │   ├── services/       # 业务逻辑层
│   │   ├── repositories/   # 数据访问层
│   │   ├── schemas/        # Pydantic 模型
│   │   └── utils/          # 工具函数
│   ├── alembic/            # 数据库迁移
│   └── requirements.txt
├── frontend/               # 前端 Vue3
│   ├── src/
│   │   ├── api/            # API 请求层
│   │   ├── components/     # 公共组件
│   │   ├── layouts/        # 布局组件
│   │   ├── router/         # 路由配置
│   │   ├── stores/         # Pinia 状态管理
│   │   ├── styles/         # 全局样式
│   │   └── views/          # 页面视图
│   └── package.json
├── docker-compose.yml      # 生产部署
├── docker-compose.dev.yml  # 开发环境
└── .gitignore
```

## 🚀 快速开始

### 环境要求

- Python 3.12+
- Node.js 18+
- PostgreSQL 16+
- Redis 7+
- Docker（可选，推荐）

### 后端启动

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填写数据库、Redis、企微等配置

# 数据库迁移
alembic upgrade head

# 启动服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 前端启动

```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:5173

### Docker 一键部署

```bash
docker-compose up -d
```

## 📊 数据库表概览

系统共 44 张表，按业务域分组：

| 业务域 | 表数量 | 主要表 |
|---|---|---|
| 组织架构 | 4 | companies, stores, employees, users |
| 订座桌台 | 3 | tables, bookings, table_sessions |
| 合同薪资 | 2 | contracts, salary_matrix |
| 考勤排班 | 8 | attendance_records, schedules, shift_configs |
| KPI 考核 | 4 | kpi_templates, kpi_scores, kpi_results |
| 业绩收款 | 3 | daily_revenue, employee_monthly_performance, wework_payment_sync |
| 工资计算 | 4 | payroll_items_config, payroll_records, salary_rules |
| 账期排名 | 2 | periods, employee_rankings |
| 其他 | 14 | 评价、审批、通知、管家、酒水、审计 |

## 🔐 安全说明

- 工资数据通过 PostgreSQL 行级安全（RLS）隔离
- SSH 密钥、数据库备份、上传文件等敏感内容已通过 `.gitignore` 排除
- 企业微信 OAuth 认证，JWT 令牌授权

## 📝 开发指南

- 后端代码遵循 PEP 8，使用 `ruff` 检查
- 前端代码遵循 ESLint + Prettier 规范
- 提交信息格式：`<type>: <description>`（如 `feat: 新增排名模块`）

## 📄 许可证

[MIT License](./LICENSE) © 2026 crushbar
