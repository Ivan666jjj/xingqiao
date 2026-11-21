# 星桥后端 API

面向自闭症谱系青少年的社交练习与记录后端。对应计划书第 07 节「架构与 API」。

设计边界：**只做练习与记录，不做诊断；不训练模型；不采集人脸、声音和精确位置。**
内容全部来自 `data/` 下的人工审核脚本，LLM 不在主链路上。

## 快速开始

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

export XQ_ADMIN_TOKEN=dev-admin-token
./run.sh                      # 127.0.0.1:8000
python3 scripts/smoke.py      # 另开一个终端跑端到端冒烟
```

打开 <http://127.0.0.1:8000/docs> 看自动生成的 OpenAPI。

测试：

```bash
python3 -m pytest -q
```

## 鉴权

两种身份，互不混用：

| 身份 | 传递方式 | 用途 |
|---|---|---|
| 管理员 / 机构 | `X-Admin-Token: <token>` | 建参与者、看群体报告、审核队列、审计、outbox |
| 参与者 | `Authorization: Bearer <token>` | 同意、练习、自评、看自己的报告、删除自己的数据 |

参与者 token 只在创建时返回一次，服务端只存 SHA-256。

## 接口

| 方法 | 路径 | 鉴权 | 说明 |
|---|---|---|---|
| GET | `/health` | 无 | 健康检查，不限流 |
| GET | `/api/v1/scenes` | 无 | 场景列表（不含答案） |
| POST | `/api/v1/participants` | 管理员 | 创建参与者，返回一次性 token |
| POST | `/api/v1/consent` | 参与者 | 记录监护人同意 + 本人知情 |
| POST | `/api/v1/sessions` | 参与者 | 开始一轮；无有效同意则 403 |
| POST | `/api/v1/sessions/{id}/turns` | 参与者 | 提交选择，返回对方回应与反馈 |
| POST | `/api/v1/emotion/quiz/submit` | 参与者 | 情境判断题作答 |
| POST | `/api/v1/tasks/{id}/checkin` | 参与者 | 线下泛化任务打卡 |
| GET | `/api/v1/reports/student/{id}` | 本人或管理员 | 练习次数、提示依赖率、平均反应时 |
| GET | `/api/v1/reports/cohort` | 管理员 | 群体聚合；**少于 10 人直接抑制** |
| GET | `/api/v1/moderation/queue` | 管理员 | 待审风险条目 |
| POST | `/api/v1/moderation/review` | 管理员 | 裁决：`escalate` / `close` |
| GET | `/api/v1/admin/audit` | 管理员 | 最近 50 条审计 |
| GET | `/api/v1/admin/outbox` | 管理员 | 已完成会话的签名事件 |
| DELETE | `/api/v1/subject` | 参与者 | 级联删除本人全部记录 |

### 最小调用链

```bash
# 1) 机构建号
curl -s -X POST localhost:8000/api/v1/participants \
  -H 'X-Admin-Token: dev-admin-token' -H 'Content-Type: application/json' \
  -d '{"code":"P-001","ageBand":"12-14","gender":"unspecified","diagnosisStatus":"diagnosed","languageLevel":"verbal"}'

# 2) 监护人同意（token 用上一步返回的）
curl -s -X POST localhost:8000/api/v1/consent \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"version":"2026-11-21","scopes":["practice"],"guardianConfirmed":true,"childAssent":true,"method":"digital"}'

# 3) 开始练习
curl -s -X POST localhost:8000/api/v1/sessions \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"sceneId":"borrow","mode":"solo"}'

# 4) 提交一回合
curl -s -X POST localhost:8000/api/v1/sessions/$SID/turns \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"turnIndex":0,"optionId":"a","latencyMs":1200,"hintLevel":0}'
```

响应里**不会**提前给出 `feedback` 或 `kind`，必须提交后才返回，防止前端抓包看答案。

## 安全与伦理（写进代码的约束）

- **同意门禁**：没有 `withdrawn_at IS NULL` 的同意记录，`sessions` / quiz / task 全部 403。
- **风险词升级**：自由输入命中自伤或暴力词，暂停会话、写入 `moderation_items`、返回固定安全话术；不调用模型，不自行判断。
- **删除权**：`DELETE /api/v1/subject` 依赖外键级联，删参与者 → 同意 / 会话 / 回合 / 自评全部清除；审计只留动作，不留内容。
- **小样本抑制**：群体报告少于 10 名参与者时只返回人数与 `suppressed: true`，不出比例。
- **日志最小化**：应用默认不打印请求体；审计详情只存动作与版本号。
- **Webhook 去标识**：事件只含 `participantId`（假名）、`sessionId`、`sceneId`、回合数与时间，不含姓名、学校、code。
- **限流**：默认每 token 每分钟 120 次；`/health` 与 `/docs` 不限。

## 数据表

`participants` · `consents` · `sessions` · `turns` · `self_reports` · `moderation_items` · `audit_log` · `webhook_outbox`

SQLite 开 WAL 与外键。schema 在 `app/db.py`，启动时自动建表。

## 部署到阿里云（2C2G 足够）

```bash
# 1. 上传
scp -r backend root@<ECS_IP>:/opt/xingqiao/

# 2. 装依赖
cd /opt/xingqiao/backend
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt

# 3. 生成两个随机密钥，写进 .env
cp .env.example .env
python3 -c 'import secrets; print("XQ_ADMIN_TOKEN="+secrets.token_hex(32)); print("XQ_WEBHOOK_SECRET="+secrets.token_hex(32))'
# 编辑 .env，并设 XQ_ALLOWED_ORIGINS=https://你的前端域名
```

`deploy/xingqiao.service` 与 `deploy/nginx.conf.example` 可直接改路径使用：

```bash
cp deploy/xingqiao.service /etc/systemd/system/
systemctl daemon-reload && systemctl enable --now xingqiao
cp deploy/nginx.conf.example /etc/nginx/conf.d/xingqiao.conf
nginx -t && systemctl reload nginx
# HTTPS 用 certbot 或阿里云免费证书
```

备份（cron 每日 3:10）：

```bash
sqlite3 /opt/xingqiao/backend/data/xingqiao.db \
  ".backup '/opt/xingqiao/backup/xq-$(date +\%F).db'"
```

## 当前明确没做的

- **Webhook 只落 outbox，不发 HTTP**：签名已生成，投递 worker 留到赛后；避免演示时外部地址不可用拖垮服务。
- **限流是进程内的**：单 worker 正确；开多 worker 需要换 Redis。
- **SQLite 单机**：一个班 / 一个机构够用，不做水平扩展。
- **没有 LLM 调用**：主链路是脚本树；自由文本只做风险词检测和存档，不生成回复。
- **没有前端**：这是 API；计划书里的 HTML 原型是另一份静态文件。

## 与计划书的对应

| 计划书 | 这里 |
|---|---|
| 07 架构 · API 草案 | 上表全部端点 |
| 07 架构 · 数据与记录 | 8 张表 + 报告口径 |
| 08 伦理 · 同意与撤回 | 同意门禁 + `DELETE /subject` |
| 08 伦理 · 内容安全 | 风险词 → 审核队列 → 人工裁决 |
| 08 伦理 · 数据最小化 | 无人脸/音频/位置；webhook 去标识 |
| 12 研究依据 | 报告用「提示依赖率 + 反应时」，不宣称症状改善 |