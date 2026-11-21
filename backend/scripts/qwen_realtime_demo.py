#!/usr/bin/env python3
"""千问实时语音对话的最小验证：WAV(PCM16 16k 单声道) → 文本 + 24k 回复音频。

用法：
  say -v Tingting -o in.aiff "你好，我今天不太敢和同学说话。"
  afconvert -f WAVE -d LEI16@16000 -c 1 in.aiff in.wav
  python3 scripts/qwen_realtime_demo.py --audio in.wav --out out.wav
"""
import argparse
import base64
import json
import os
import ssl
import subprocess
import wave

import certifi
from websockets.sync.client import connect

INSTRUCTIONS = (
    "你是星桥的社交练习陪练。用简短、温和的中文回应。"
    "不诊断、不给医疗建议、不要求眼神接触、不承诺疗效。每次最多三句话。"
)


def api_key() -> str:
    key = os.getenv("QWEN_API_KEY", "")
    if key:
        return key
    try:
        return subprocess.check_output(
            ["security", "find-generic-password", "-s", "qwen-dashscope-key", "-w"],
            text=True,
        ).strip()
    except Exception as exc:
        raise SystemExit("缺少 QWEN_API_KEY，且钥匙串 qwen-dashscope-key 不可读") from exc


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", required=True)
    ap.add_argument("--out", default="realtime_out.wav")
    ap.add_argument(
        "--url",
        default=os.getenv(
            "QWEN_WS_URL", "wss://dashscope.aliyuncs.com/api-ws/v1/realtime"
        ),
    )
    ap.add_argument(
        "--model",
        default=os.getenv("QWEN_REALTIME_MODEL", "qwen3.8-omni-flash-realtime"),
    )
    args = ap.parse_args()

    src = wave.open(args.audio, "rb")
    pcm = src.readframes(src.getnframes())
    src.close()
    if len(pcm) == 0:
        raise SystemExit("输入 WAV 为空")

    ctx = ssl.create_default_context(cafile=certifi.where())
    url = f"{args.url}?model={args.model}"

    with connect(
        url,
        additional_headers={"Authorization": f"Bearer {api_key()}"},
        ssl=ctx,
        open_timeout=15,
        max_size=None,
    ) as ws:
        first = json.loads(ws.recv(timeout=15))
        print("session:", first.get("type"))

        ws.send(
            json.dumps(
                {
                    "type": "session.update",
                    "session": {
                        "modalities": ["text", "audio"],
                        "instructions": INSTRUCTIONS,
                        "audio": {
                            "input": {"format": {"type": "pcm", "sample_rate": 16000}},
                            "output": {
                                "format": {"type": "pcm", "sample_rate": 24000}
                            },
                        },
                        "turn_detection": None,
                    },
                },
                ensure_ascii=False,
            )
        )
        while True:
            ev = json.loads(ws.recv(timeout=15))
            if ev.get("type") in ("session.updated", "error"):
                if ev["type"] == "error":
                    raise SystemExit(json.dumps(ev, ensure_ascii=False)[:500])
                break

        for i in range(0, len(pcm), 4800):
            ws.send(
                json.dumps(
                    {
                        "type": "input_audio_buffer.append",
                        "audio": base64.b64encode(pcm[i : i + 4800]).decode(),
                    }
                )
            )
        ws.send(json.dumps({"type": "input_audio_buffer.commit"}))

        while True:
            ev = json.loads(ws.recv(timeout=15))
            if ev.get("type") in ("input_audio_buffer.committed", "error"):
                break

        ws.send(json.dumps({"type": "response.create"}))

        audio = bytearray()
        transcript = ""
        heard = ""
        while True:
            ev = json.loads(ws.recv(timeout=30))
            kind = ev.get("type", "")
            if kind == "conversation.item.input_audio_transcription.delta":
                heard += ev.get("delta", "")
            elif kind == "response.audio_transcript.delta":
                transcript += ev.get("delta", "")
            elif kind == "response.audio.delta":
                audio += base64.b64decode(ev.get("delta", ""))
            if kind in ("response.done", "error"):
                if kind == "error":
                    print("error:", json.dumps(ev, ensure_ascii=False)[:500])
                break

    print("heard:", heard)
    print("reply:", transcript)
    print("audio bytes:", len(audio))
    if audio:
        out = wave.open(args.out, "wb")
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(24000)
        out.writeframes(bytes(audio))
        out.close()
        print("saved:", args.out)


if __name__ == "__main__":
    main()