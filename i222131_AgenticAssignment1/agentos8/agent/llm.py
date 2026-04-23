from __future__ import annotations
import os, json, subprocess, urllib.request, urllib.error, ssl
from typing import Optional

class LLM:
    '''
    Minimal LLM wrapper (stdlib only).
    Tests monkeypatch this class, so keep interface stable.
    '''
    def __init__(self, backend: str = "ollama", timeout_s: int = 60):
        self.backend = backend.lower()
        self.timeout_s = timeout_s

    def complete(self, prompt: str) -> str:
        if self.backend == "ollama":
            return self._ollama(prompt)
        if self.backend == "groq":
            return self._groq(prompt)
        raise ValueError("backend must be 'ollama' or 'groq'")

    def _ollama(self, prompt: str) -> str:
        model = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")
        p = subprocess.run(
            ["ollama", "run", model],
            input=prompt.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=self.timeout_s
        )
        out = p.stdout.decode("utf-8", errors="ignore").strip()
        if not out:
            err = p.stderr.decode("utf-8", errors="ignore")
            raise RuntimeError(f"Ollama empty output. stderr={err[:250]}")
        return out

    def _groq(self, prompt: str) -> str:
        api_key = os.getenv("GROQ_API_KEY")
        model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY is not set")

        url = "https://api.groq.com/openai/v1/chat/completions"
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url, data=data,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        )
        try:
            # Try to use certifi's CA bundle for SSL verification; fall back to system certs if unavailable
            context = None
            try:
                import certifi
                context = ssl.create_default_context(cafile=certifi.where())
            except ImportError:
                context = ssl.create_default_context()
            
            with urllib.request.urlopen(req, timeout=self.timeout_s, context=context) as resp:
                raw = resp.read().decode("utf-8", errors="ignore")
        except urllib.error.HTTPError as e:
            # Capture the actual response body for debugging HTTP errors
            try:
                error_body = e.read().decode("utf-8", errors="ignore")
                raise RuntimeError(f"Groq HTTP {e.code}: {error_body}") from e
            except Exception:
                raise RuntimeError(f"Groq request failed with HTTP {e.code}: {e}") from e
        except urllib.error.URLError as e:
            raise RuntimeError(f"Groq request failed: {e}") from e

        obj = json.loads(raw)
        return obj["choices"][0]["message"]["content"].strip()
