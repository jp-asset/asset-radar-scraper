"""Funções de normalização partilhadas por todos os scrapers."""
import re


def parse_price(text) -> float | None:
    if not text:
        return None
    if isinstance(text, (int, float)):
        return float(text)
    cleaned = re.sub(r"[^\d.,]", "", str(text))
    if not cleaned:
        return None
    has_dot = "." in cleaned
    has_comma = "," in cleaned
    if has_dot and has_comma:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif has_comma and not has_dot:
        decimals = cleaned.split(",")[-1]
        cleaned = cleaned.replace(",", ".") if len(decimals) <= 2 else cleaned.replace(",", "")
    elif has_dot and not has_comma:
        decimals = cleaned.split(".")[-1]
        if len(decimals) > 2:
            cleaned = cleaned.replace(".", "")
        elif cleaned.count(".") > 1:
            cleaned = cleaned.replace(".", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_area(text) -> float | None:
    if not text:
        return None
    if isinstance(text, (int, float)):
        return float(text)
    match = re.search(r"(\d+[.,]?\d*)\s*m", str(text), re.IGNORECASE)
    if not match:
        return None
    val = match.group(1).replace(",", ".")
    try:
        return float(val)
    except ValueError:
        return None


def clean_text(text) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", str(text)).strip()
