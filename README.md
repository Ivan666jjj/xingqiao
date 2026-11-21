# 星桥 · 自闭症青少年社会生活练习与记录平台

48 小时黑客松项目：一份可交互的计划书，加一套已经跑通测试的后端 API。

- 在线页面：https://ivan666jjj.github.io/xingqiao/
- 计划书与可玩原型：`index.html`（同 `星桥_黑客松计划书_20261121.html`）
- 文献与数据底稿：`星桥_文献与数据底稿_20261121.md`
- 后端：`backend/`

## 这个页面是什么

单文件 HTML，无外部依赖，可离线打开。里面有一个可以直接点的社交脚本原型（三个场景），以及计划书全文：问题、模块、48 小时排班、三人分工、架构与 API、伦理、评审对照、风险、赛后路线。

## 后端是什么

FastAPI + SQLite，37 个测试，18 个端点：

- 同意门禁：没有有效同意不能开始练习
- 风险词升级：自伤/暴力词暂停会话并进入人工审核队列
- 删除权：删除主体时级联清除会话、回合、同意记录
- 小样本抑制：群体报告少于 10 人不出比例
- 已签名事件 outbox（Webhook 投递 worker 尚未实现）

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q
./run.sh
```

详见 [`backend/README.md`](backend/README.md)。

## 本地 ServBay 演示（页面 + API 同域）

- 地址：<http://xingqiao.localhost/>
- 静态目录：`/Applications/ServBay/www/xingqiao`
- Apache vhost：`/Applications/ServBay/package/etc/apache/vhosts/xingqiao.conf`
  （可复制 [`backend/deploy/servbay-vhost.conf.example`](backend/deploy/servbay-vhost.conf.example)）
- `/api`、`/health`、`/docs`、`/openapi.json` 反代到 `127.0.0.1:8000`

使用顺序：

```bash
cd backend && ./run.sh                      # 先起 API
cp index.html /Applications/ServBay/www/xingqiao/index.html
```

页面工具条会自动探测同源 API：连上显示「本地 API 已连接 · 3 个场景」，连不上显示「离线脚本模式」，两种情况都能完整演示。

## 部署边界

GitHub Pages 只能托管静态页面。这里的在线页面是**前端与计划书**；API 需要部署到阿里云等能跑 Python 的服务器，再把 `XQ_ALLOWED_ORIGINS` 指到 Pages 域名。

## 数据与伦理

- 页面内置脚本与演示数据均为合成内容，不含任何真实未成年人信息。
- 产品定位是练习与记录，**不做诊断、不承诺改善核心症状**。
- 不采集人脸、声音、精确位置；不训练模型。