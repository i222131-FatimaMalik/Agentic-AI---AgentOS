from __future__ import annotations

INJECTION_MARKERS = [
    "IGNORE PREVIOUS", "SYSTEM:", "DEVELOPER:", "You must reveal", "print secrets",
    "override", "act as system", "exfiltrate", "API key"
]

def sanitize_observation(obs: str) -> str:
    # Light-touch sanitization: remove obvious injection markers while retaining content.
    out = obs
    for m in INJECTION_MARKERS:
        out = out.replace(m, "[redacted]")
    return out
