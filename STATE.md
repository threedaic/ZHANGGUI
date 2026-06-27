# Crush掌柜 — 当前状态看板（STATE.md）

> **AI 会话开始必读**：本文件是项目唯一"当前状态"真相源。每次会话开始先读这里，再读 git log，再开始干活。
>
> **AI 部署后必更新**：每次部署到服务器、每次数据库变更、每次大改动，必须更新本文件并 git commit。
>
> 最后更新：2026-06-28

---

## 一、环境信息

| 项 | 值 |
|----|-----|
| 代码仓库（本地） | `c:\Users\hello\Documents\trae_projects\crush-zhanggui` |
| 远程仓库 | `git@github.com:threedaic/ZHANGGUI.git` |
| 当前分支 | `trae/generated-code` |
| 服务器 IP | 49.233.181.87（腾讯云 Ubuntu 22.04） |
| 线上域名 | https://zhanggui.crushserver.cloud/ |
| SSH | `ssh -i C:/Users/hello/Downloads/Crush3dai.pem root@49.233.181.87` |

## 二、服务运行状态（服务器）

| 容器 | 端口 | 用途 |
|------|------|------|
| crush-zhanggui-api | 8001 | 后端 FastAPI |
| crush-zhanggui-db | 5432 | PostgreSQL 16（容器内5432，宿主机映射5433） |
| crush-redis | 6379 | Redis 7 |

**数据库连接（线上）：** `crush_app / UXIe8QzwOLNjE3SWSImGhXbv6z_aCZhu / crush_zhanggui`

## 三、当前线上版本

| 项 | 值 |
|----|-----|
| 最后部署时间 | 2026-06-28 之前（具体时间待对齐） |
| 线上对应 commit | 待对齐（服务器是 tar 上传，非 git pull） |
| 本地领先远程 | 0 commit（本次收拾后归零） |

## 四、账号体系（详见 SPEC §0.6）

| 账号 | 密码 | 角色 | 绑定员工 | 门店 | 用途 |
|------|------|------|---------|------|------|
| admin | admin123 | system_admin | 周鹏飞 | 总部 | 网页调试/开发/运维 |

- **网页登录**：`/login` → admin / admin123
- **企微登录**：OAuth 免密（按 wecom_user_id 匹配员工）
- **禁止**：私自创建新账号（详见 SPEC §0.6.3）

## 五、数据库最后变更

| 时间 | 变更内容 | 操作方式 |
|------|---------|---------|
| 2026-06-28 | admin 账号密码改 admin123 + 绑定周鹏飞 + 删除"周鹏飞"独立账号 | 直接 SQL（未补迁移文件，待补） |

## 六、开发工作流铁律（AI 必须遵守）

1. **代码/文档只在本地改**，服务器上禁止直接改代码
2. **改完立刻 git commit**，commit message 写清楚改了啥
3. **每次 commit 后 git push** 到 GitHub
4. **数据库改动**必须先写 SQL 文件进 `backend/alembic/versions/`，git commit，再在服务器执行
5. **部署走统一脚本**（后端 tar+rebuild，前端 build+上传 dist）
6. **部署后必须更新本文件**（STATE.md）并 commit

## 七、未部署的本地改动

> 本次收拾后清空。以后每次新改动 AI 自动追加到这里，部署后清空。

（无）

## 八、最近 5 次 commit

> AI 会话开始时用 `git log --oneline -5` 查看，了解最近改动。

---

**维护规则**：本文件由 AI 维护，用户不需要手动改。每次部署、每次大改动、每次数据库变更，AI 必须更新本文件。
