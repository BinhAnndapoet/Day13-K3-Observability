from __future__ import annotations

import hashlib
import re

# Tu khoa dia chi tieng Viet. Dat "thanh pho" truoc "pho" de alternation khong
# cat ngan match, va cho phep so nha dung truoc tu khoa.
_ADDRESS_KEYWORDS = r"thành phố|số nhà|đường|phố|ngõ|phường|xã|quận|huyện|tỉnh"

PII_PATTERNS: dict[str, re.Pattern[str]] = {
    "email": re.compile(r"[\w\.-]+@[\w\.-]+\.\w+"),
    "phone_vn": re.compile(r"(?<!\d)(?:\+84|0)(?:[ .-]?\d){9}(?!\d)"),
    "cccd": re.compile(r"\b\d{12}\b"),
    "credit_card": re.compile(r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b"),
    "passport": re.compile(r"\b[A-Z]\d{7}\b"),
    # Che ca tu khoa lan gia tri di kem (ten duong, so nha), khong chi che tu khoa.
    "address_vn": re.compile(
        rf"(?:\d+[\w/]*\s+)?(?:{_ADDRESS_KEYWORDS})\s+[^,;.\n]{{1,40}}",
        re.IGNORECASE,
    ),
}


def scrub_text(text: str) -> str:
    safe = text
    for name, pattern in PII_PATTERNS.items():
        safe = pattern.sub(f"[REDACTED_{name.upper()}]", safe)
    return safe


def summarize_text(text: str, max_len: int = 80) -> str:
    safe = scrub_text(text).strip().replace("\n", " ")
    return safe[:max_len] + ("..." if len(safe) > max_len else "")


def hash_user_id(user_id: str) -> str:
    return hashlib.sha256(user_id.encode("utf-8")).hexdigest()[:12]
