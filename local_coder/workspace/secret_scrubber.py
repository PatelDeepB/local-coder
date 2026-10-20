"""Prevents secret credentials, keys, and tokens from leaking into prompts."""

from pathlib import Path
import re


class SecretScrubber:
    """Scans and redacts passwords, tokens, private keys, and sensitive environment files."""

    SENSITIVE_FILENAMES = frozenset({
        ".env",
        ".env.local",
        ".env.production",
        "id_rsa",
        "id_ed25519",
        "private_key.pem",
        "credentials.json",
    })

    SECRET_PATTERNS = (
        re.compile(r"(?i)(api[_-]?key|secret|token|password|auth|bearer)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-\.]{8,})['\"]?"),
        re.compile(r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----.*?-----END (?:RSA |EC )?PRIVATE KEY-----", re.DOTALL),
        re.compile(r"ghp_[a-zA-Z0-9]{36}"),
        re.compile(r"sk-[a-zA-Z0-9]{48}"),
    )

    def is_sensitive_file(self, file_path: str | Path) -> bool:
        """Returns True if the file name matches sensitive credential filenames."""
        p = Path(file_path)
        return p.name in self.SENSITIVE_FILENAMES or p.name.startswith(".env")

    def sanitize_text(self, text: str) -> str:
        """Redacts identified secrets with [REDACTED_SECRET]."""
        cleaned = text
        for pat in self.SECRET_PATTERNS:
            cleaned = pat.sub(r"\1: [REDACTED_SECRET]", cleaned)
        return cleaned
