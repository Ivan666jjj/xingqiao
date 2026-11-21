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
| POST | `/api/v1/coach/reply` | 参与者 | 受限陪练：给 2 条可试说法 + 理由；不做开放式生成 |
| GET | `/api/v1/reports/cohort` | 管理员 | 群体聚合；**少于 10 人直接抑制** |
| GET | `/api/v1/moderation/queue` | 管理员 | 待审风险条目 |
| POST | `/api/v1/moderation/review` | 管理员 | 裁决：`escalate` / `close` |
| GET | `/api/v1/admin/audit` | 管理员 | 最近 50 条审计 |
| GET | `/api/v1/admin/outbox` | 管理员 | 已完成会话的签名事件 |
| POST | `/api/v1/safety/check` | 管理员 | 输出侧护栏：模型草稿先过规则再发 |
| GET | `/api/v1/rules` | 管理员 | 负规则目录、安全短语与 BCC 证据 |
| GET | `/api/v1/corpus/stats` | 管理员 | 语料库统计（仅话语观察用途） |
| GET | `/api/v1/corpus/search?q=` | 管理员 | 清洁语料检索（不供聊天使用） |
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

## 语料清洗（BCC 自闭症语料）

来源：北京语言大学 BCC 语料库，扩展检索 6 个词，原始 3,610 条。清洗命令：

```bash
python3 scripts/clean_corpus.py --zip /path/to/BCC_自闭症_语料.zip --out data/corpus
python3 scripts/import_corpus.py --dir data/corpus --db data/xingqiao.db
```

当前结果：

| 状态 | 条数 | 去向 |
|---|---|---|
| clean | 2,118 | 入库，`purpose=discourse`，仅管理员检索 |
| review | 143 | 本地留存，待人工复核，不入库 |
| quarantine | 906 | 本地留存，不展示、不入库 |

规则：PII 脱敏（手机/邮箱/证件/账号）、性/自伤/暴力内容隔离、口语与近代汉语频道隔离、污名化与治愈叙事与错误归因降级、归一化去重。

**重要边界**：BCC 是新闻/文学/网络话语的上下文切片，不是干预指南或临床语料。它只用于「人们怎么谈论自闭症」的词表与话语观察，**不进入聊天检索，不作为给孩子的回答依据**。语料受 BCC 使用条款约束，`data/raw/` 与 `data/corpus/` 已在 `.gitignore`，不要随公开仓库分发。

队内交付 zip 中额外包含 `data/raw/`（原始 zip + 解压 CSV）与 `data/corpus/` 的 clean/review/report，方便队友离线复现；`quarantine.jsonl` 不直接放入，需要时用 `clean_corpus.py` 从原始 zip 重建。**这个 zip 只发队内，不再二次公开。**

「BCC 能不能支撑开放式 AI 陪伴」的专项审计见 [`docs/companion-corpus-audit.md`](docs/companion-corpus-audit.md)：3,610 条里严格筛完只剩 22 条，可用多轮对话为 0。

## 关于「AI 聊天」：做的是受限陪练

`POST /api/v1/coach/reply` 不做开放式聊天，只做三件事：

1. 识别这句话的意图（请求/命令/回避/接受拒绝/道歉/辩解等）；
2. 返回 2 条可以照着试的说法，以及每条为什么；
3. 命中自伤/暴力词时停止生成、升级人工审核。

没有模型自由生成、没有长期记忆、没有「AI 朋友」人格。理由：面向未成年人，开放式陪伴会带来依赖、错误建议和危机处理风险；而 BMJ 2023 的证据显示，起作用的通常是结构化练习与成人反馈，不是模型规模。

如果赛后要接 LLM，只允许作为「把审核过的建议改写得更自然」的受约束层，并且必须保留同一套风险拦截与人工复核。

## 输出侧负规则包（开放式陪伴用）

如果接入方要接自己的 LLM 做开放陪伴，**在把模型草稿发给用户之前**调用：

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/safety/check \
  -H 'X-Admin-Token: <token>' -H 'Content-Type: application/json' \
  -d '{"text":"自闭症是可以治愈的。"}'
```

返回 `allowed`、命中的规则、原因和 `safeAlternatives`。`allowed:false` 时必须重写或换成安全表达。

规则共 13 条，分治愈叙事、诊断断言、污名化、强迫眼神、正常化压力、医疗建议、依赖诱导、否定感受、空头保证、夸大效果、危机淡化、索要隐私、幼儿化。BCC 直接支持其中五类（治愈 42 条、污名 123 条、诊断 2 条、正常化 2 条、危机淡化 2 条），其余来自研究与伦理要求。

完整接入说明：[`docs/rule-pack.md`](docs/rule-pack.md)。

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