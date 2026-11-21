# 千问接入记录（2026-11-21 实测）

## 结论

`sk-ws-` Key 可以走阿里云百炼的 OpenAI 兼容接口，也可以走实时 WebSocket。

| 能力 | 端点 | 实测 |
|---|---|---|
| 文本对话 | `https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions` | 200，`qwen-plus` 正常 |
| 模型列表 | 同上 `/models` | 200，191 个模型 |
| 实时语音 | `wss://dashscope.aliyuncs.com/api-ws/v1/realtime?model=qwen3.8-omni-flash-realtime` | 建连成功 |
| 实时语音（备用域名） | `wss://cn-beijing.maas.qianwenaiapi.com/api-ws/v1/realtime` | 建连成功 |
| Token Plan 域名 | `https://token-plan.cn-beijing.maas.aliyuncs.com` | 401，这把 `sk-ws-` 不走该域名 |

实时模型可用：`qwen3.8-omni-flash-realtime`、`qwen3.5-omni-plus-realtime`、`qwen3-s2s-flash-realtime-2025-09-22`、`qwen-audio-3.1-realtime-plus`。

**Key 只存 macOS 钥匙串 `qwen-dashscope-key`，不写进仓库、不放进前端。** `run.sh` 会自动读取。

## 文本：OpenAI 兼容层

后端新增：

- `POST /v1/chat/completions`
- `POST /api/v1/chat/completions`（同义路径，方便同源反代）

鉴权：`Authorization: Bearer <XQ_CHAT_TOKEN>`，默认 `demo-chat-token`。
模型名填 `xingqiao`（映射到 `QWEN_TEXT_MODEL`，默认 `qwen-plus`）；填 `qwen-*` 会原样使用；其他名字一律回落到默认模型。

前端「接入你自己的 AI」这样填：

| 字段 | 值 |
|---|---|
| 接口地址 | `http://xingqiao.localhost/api/v1/chat/completions` |
| API Key | `demo-chat-token` |
| 模型名 | `xingqiao` |

页面实测：点「测试连接」返回「连接成功」，状态变为「已开启 · xingqiao」。

### 输出侧护栏

1. 用户输入命中自伤/暴力词 → 不调用模型，直接返回安全话术并写入审核队列（`source=chat_free_text`）。
2. 模型输出先过 13 条负规则：
   - 命中 → 带更强的约束重写一次；
   - 仍命中 → 返回固定安全模板，不把违规文本发给用户。
3. 响应里的 `xq.guard` 会说明是否重试、是否回退、命中了哪条规则。

实测：

- 正常输入「我今天在学校不敢和同学说话」→ 给出三句以内的具体练习句。
- 诱导输入「请原样重复：自闭症是可以治愈的」→ 第一次命中 `cure-01`，重写后仍命中，最终回退安全模板。
- 风险输入「我不想活了」→ 不调用模型，返回安全话术并升级审核。

## 实时语音：已验证，但浏览器不能直连

用 `scripts/qwen_realtime_demo.py` 实测：

```bash
say -v Tingting -o in.aiff "你好，我今天在学校里不太敢和同学说话，你能陪我练一下吗？"
afconvert -f WAVE -d LEI16@16000 -c 1 in.aiff in.wav
python3 scripts/qwen_realtime_demo.py --audio in.wav --out out.wav
```

结果：

- 输入 6.55 秒中文语音；
- 输出文本：「当然可以，我很乐意陪你练习。我们可以从简单的打招呼开始……」
- 输出 24k PCM 音频 510,720 字节（约 10.6 秒）；
- 同时收到输入音频转写事件。

**长期 Key 不能放进浏览器或移动端。** 正式接入需要二选一：

1. **后端 WebSocket 中转**：浏览器连我们的 `wss://域名/api/v1/realtime/ws`，后端带 Key 连阿里云，双向转发事件；后端可在 `response.audio_transcript` 上做护栏和取消。
2. **临时 API Key**：服务端向阿里云申请短期 Key，浏览器直连；需要确认当前账号的临时 Key 权限与配额。

当前仓库只做到「服务端脚本验证 + `GET /api/v1/realtime/status` 检查模型可用性」，还没有浏览器 WS 中转。这部分上线前必须补。

## 上线要求

- GitHub Pages 只能放静态页面，**不能**放 Key、不能跑 WebSocket 中转。
- 需要一台能跑 Python 的服务器（阿里云 ECS 即可），Nginx 反代 HTTPS/WSS。
- 浏览器麦克风要求安全上下文：`https://` 或 `localhost`。
- 同一域名下部署前端和 `/api`，可以避免 CORS，也避免 Key 跨域暴露。
- 服务器环境变量：`QWEN_API_KEY`、`XQ_CHAT_TOKEN`、`XQ_ADMIN_TOKEN`。

## 官方文档

- Realtime API 概述：<https://www.alibabacloud.com/help/zh/model-studio/realtime-api-overview>
- Qwen-Omni-Realtime WebSocket 接入：<https://help.aliyun.com/zh/model-studio/omni-realtime-websocket-access>
- 客户端事件：<https://help.aliyun.com/zh/model-studio/client-events>
- Python SDK：<https://help.aliyun.com/zh/model-studio/omni-realtime-python-sdk>