"""Funções de normalização partilhadas por todos os scrapers."""
import re
import logging

log = logging.getLogger("asset_radar")

# Nenhum artigo real neste catálogo (imóvel, carro, relógio, moda, arte)
# custa mais do que isto. Serve de rede de segurança contra bugs de parsing
# silenciosos (visto em produção: um campo de preço que na verdade era um
# objecto {"EUR":.., "USD":.., "GBP":..} foi stringificado e todos os
# dígitos concatenados num único número de centenas de mil milhões de euros).
_MAX_PLAUSIBLE_PRICE = 50_000_000


def parse_price(text) -> float | None:
    if not text:
        return None
    # NUNCA stringificar dicts/listas — str({"EUR":6200,"USD":6700}) dá
    # "{'EUR': 6200, 'USD': 6700}", e o passo seguinte extrai TODOS os
    # dígitos e concatena-os num número sem sentido. Se o chamador recebeu
    # uma estrutura em vez de um valor escalar, tem de extrair o campo
    # certo antes de chamar parse_price — aqui devolvemos None em vez de
    # inventar um número.
    if isinstance(text, (dict, list, tuple, set)):
        log.warning(f"[normalize] parse_price recebeu uma estrutura, não um escalar — ignorado: {type(text).__name__}")
        return None
    if isinstance(text, (int, float)):
        value = float(text)
    else:
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
            value = float(cleaned)
        except ValueError:
            return None
    if value < 0 or value > _MAX_PLAUSIBLE_PRICE:
        log.warning(f"[normalize] parse_price: valor implausível descartado ({value}), raw={text!r}")
        return None
    return value


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
