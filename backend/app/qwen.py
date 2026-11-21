import certifi
import httpx


class QwenError(RuntimeError):
    pass


class QwenClient:
    def __init__(self, api_key: str, base_url: str, model: str, timeout: float = 60):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def chat(
        self,
        messages: list[dict],
        model: str | None = None,
        max_tokens: int = 400,
        temperature: float = 0.6,
    ) -> dict:
        if not self.api_key:
            raise QwenError("qwen_api_key_missing")
        payload = {
            "model": model or self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        try:
            with httpx.Client(
                timeout=self.timeout, verify=certifi.where(), trust_env=False
            ) as client:
                r = client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self._headers(),
                    json=payload,
                )
        except httpx.HTTPError as exc:
            raise QwenError(f"network_error:{type(exc).__name__}") from exc
        if r.status_code != 200:
            raise QwenError(f"http_{r.status_code}:{r.text[:200]}")
        return r.json()

    def models(self) -> list[str]:
        if not self.api_key:
            raise QwenError("qwen_api_key_missing")
        try:
            with httpx.Client(
                timeout=self.timeout, verify=certifi.where(), trust_env=False
            ) as client:
                r = client.get(f"{self.base_url}/models", headers=self._headers())
        except httpx.HTTPError as exc:
            raise QwenError(f"network_error:{type(exc).__name__}") from exc
        if r.status_code != 200:
            raise QwenError(f"http_{r.status_code}:{r.text[:200]}")
        return [m["id"] for m in r.json().get("data", [])]