# 星桥 · 前后端小组试用包

日期：2026-11-21

## 包内结构

```
frontend/
├── index.html                     首页（四个展品入口 + 自选 AI）
├── 展品1-社交脚本对话.html         ① 对话练习
├── 展品2-情绪情境练习.html         ② 情绪判断
├── 展品3-泛化任务卡.html           ③ 任务卡
├── 展品4-学习与情绪记录.html       ④ 学习记录
└── assets/                       共享样式与数据层
backend/                           FastAPI + SQLite + 千问接入
阿里云服务器租用与部署指南.md
README_小组试用.md
```

## 本机最快跑起来（不用服务器）

需要 Python 3.11+。

### 1. 启动后端

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
./run.sh
```

macOS 会从钥匙串 `qwen-dashscope-key` 读取千问 Key；没有 Key 也能跑，只是 AI 会走内置兜底。
Linux/Windows 请先设置：

```bash
export QWEN_API_KEY=你的百炼Key
export XQ_CHAT_TOKEN=demo-chat-token
./run.sh
```

### 2. 启动前端

另开一个终端，在包根目录：

```bash
python3 -m http.server 8080 -d frontend
```

打开 <http://127.0.0.1:8080/>。

### 3. 接上千问

首页底部「接入你自己的 AI」填：

| 字段 | 值 |
|---|---|
| 接口地址 | `http://127.0.0.1:8000/api/v1/chat/completions` |
| API Key | `demo-chat-token`（与后端 `XQ_CHAT_TOKEN` 一致） |
| 模型名 | `xingqiao` |

点「测试连接」→「连接成功」→ 打开开关。之后 ① 的对话会走千问；失败自动回退内置陪练。

### 4. 四个展品怎么试

- ① 选场景 → 点一句 → 对方回应；可打字、提示、结束保存并做情绪自评。
- ② 8 道情境题，答完写入学习记录；答错只展示“另一种可能”。
- ③ 任务卡打卡，写一句这次怎么用的。
- ④ 看本周统计、最近记录、导出 CSV。

## 放到公网

见 [`阿里云服务器租用与部署指南.md`](阿里云服务器租用与部署指南.md)。要点：

- GitHub Pages 只能放前端，不能跑后端/实时语音，也不能藏 Key；
- 需要一台阿里云 ECS（2C2G 够），Nginx 同源部署 `frontend/` + `/api/` 反代；
- 麦克风需要 HTTPS；大陆域名需要备案；
- 上线前务必替换 `XQ_ADMIN_TOKEN`、`XQ_CHAT_TOKEN`。

## 已验证

- 后端 `pytest`：56 项全过。
- 千问文本：`qwen-plus` 正常；诱导违规会被负规则拦截并重写/回退。
- 千问实时语音：`qwen3.8-omni-flash-realtime` 音频往返实测通过（服务端脚本，不是浏览器）。
- 四个页面：真实浏览器点击通过，手机宽度无横向溢出。

## 注意

- 千问 Key **不在包里**，也不要在前端填长期 Key；只放服务器环境变量。
- 包内 BCC 原始语料仅限队内复现，不要公开上传或二次分发。
- 产品定位是练习与记录，不做诊断、不承诺改善核心症状。
- 浏览器实时语音中转尚未实现；当前 ① 是文字对话，实时语音能力见 `backend/docs/qwen-integration.md`。