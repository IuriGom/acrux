"""Bounded, redacted command evidence capture."""

from __future__ import annotations

import re


def cap_text(text: str, limit: int = 16384) -> tuple[str, bool]:
    encoded = text.encode("utf-8")
    if len(encoded) <= limit:
        return text, False
    return encoded[:limit].decode("utf-8", errors="ignore"), True


def redact_text(text: str) -> str:
    text = re.sub(
        r"-----BEGIN [^-]+-----.*?-----END [^-]+-----",
        "[REDACTED]",
        text,
        flags=re.DOTALL,
    )
    text = re.sub(r"(?i)\b(Bearer\s+)[^\s]+", r"\1[REDACTED]", text)
    text = re.sub(
        r"(?i)\b(api[_-]?key|api[_-]?token|token|password|secret)(\s*[:=]\s*)([^\s,;]+)",
        r"\1\2[REDACTED]",
        text,
    )
    text = re.sub(r"(?i)\b(https?://)[^/\s:@]+:[^/\s@]+@", r"\1[REDACTED]@", text)
    return re.sub(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b", "[REDACTED]", text)


def normalize_error(exit_code: int, stdout: str, stderr: str) -> str:
    if exit_code == 0:
        return ""
    text = redact_text(stderr or stdout)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return f"exit {exit_code}"
    error_lines = [
        line
        for line in lines
        if re.search(r"(?i)error|exception|traceback|failed|panic", line)
    ]
    signature = error_lines[-1] if error_lines else lines[-1]
    signature = re.sub(r"(?:[A-Za-z]:)?/[^\s:]+", "<path>", signature)
    signature = re.sub(r"\bline\s+\d+\b", "line <n>", signature, flags=re.IGNORECASE)
    signature = re.sub(r":\d+(?=\b)", ":<n>", signature)
    signature = re.sub(r"0x[0-9a-fA-F]+", "<address>", signature)
    signature = re.sub(
        r"\b\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?\b",
        "<timestamp>",
        signature,
    )
    signature = " ".join(signature.split())
    return f"exit {exit_code}: {signature}"
