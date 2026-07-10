"""
Core Apify client para o Asset Radar Scraper Engine.

Arquitectura:
- 6 fontes principais: actors prontos do Apify marketplace (zero manutenção de seletores)
- 8 fontes secundárias: Cheerio Scraper genérico com seletores nossos (manutenção ocasional)

Limites configurados para o plano free ($5/mês):
- MAX_RESULTS_PER_SOURCE = 50 → custo total ~$1,15 por scan
- Para plano pago: aumentar para 200-500 resultados por fonte

SEGURANÇA: A API key é lida de APIFY_API_KEY (variável de ambiente / GitHub Secret).
Nunca deve aparecer no código ou em logs.
"""
import os
import logging
import time
from typing import Optional

log = logging.getLogger("asset_radar")

# Limite de resultados por fonte — controla o custo do scan
# Free ($5/mês): 50 → ~$1,15/scan, ~4 scans possíveis
# Starter ($29/mês): 200 → ~$4,60/scan, ~6 scans/dia possíveis
MAX_RESULTS_PER_SOURCE = int(os.environ.get("MAX_RESULTS_PER_SOURCE", "50"))


def get_apify_client():
    """Cria cliente Apify autenticado via variável de ambiente."""
    from apify_client import ApifyClient
    api_key = os.environ.get("APIFY_API_KEY", "")
    if not api_key:
        raise ValueError(
            "APIFY_API_KEY não definida. "
            "Adiciona como Secret no GitHub: Settings → Secrets → Actions → APIFY_API_KEY"
        )
    return ApifyClient(api_key)


def run_actor(actor_id: str, run_input: dict, timeout_secs: int = 120) -> list[dict]:
    """
    Corre um actor do Apify marketplace e devolve os resultados como lista de dicts.
    """
    client = get_apify_client()
    log.info(f"[Apify] A correr actor {actor_id} (max {MAX_RESULTS_PER_SOURCE} resultados)")
    start = time.time()
    try:
        run = client.actor(actor_id).call(
            run_input=run_input,
            timeout_secs=timeout_secs,
            memory_mbytes=256,
        )
        dataset_id = run.get("defaultDatasetId")
        if not dataset_id:
            log.warning(f"[Apify] {actor_id}: sem dataset no resultado")
            return []
        items = list(client.dataset(dataset_id).iterate_items())
        elapsed = round(time.time() - start, 1)
        log.info(f"[Apify] {actor_id}: {len(items)} resultados em {elapsed}s")
        return items
    except Exception as e:
        elapsed = round(time.time() - start, 1)
        log.error(f"[Apify] {actor_id} falhou após {elapsed}s: {e}")
        return []


def run_cheerio_scraper(start_urls: list[str], page_function: str,
                         timeout_secs: int = 120) -> list[dict]:
    """
    Corre o Cheerio Scraper genérico do Apify para fontes sem actor dedicado.
    Apenas compute units — sem fee de actor. ~$0,05 por 50 páginas.
    """
    client = get_apify_client()
    log.info(f"[Apify Cheerio] A correr em {len(start_urls)} URLs")
    start = time.time()
    try:
        run = client.actor("apify/cheerio-scraper").call(
            run_input={
                "startUrls": [{"url": u} for u in start_urls],
                "pageFunction": page_function,
                "maxRequestsPerCrawl": MAX_RESULTS_PER_SOURCE,
                "maxConcurrency": 3,
                "requestHandlerTimeoutSecs": 30,
            },
            timeout_secs=timeout_secs,
            memory_mbytes=256,
        )
        dataset_id = run.get("defaultDatasetId")
        if not dataset_id:
            return []
        items = list(client.dataset(dataset_id).iterate_items())
        elapsed = round(time.time() - start, 1)
        log.info(f"[Apify Cheerio] {len(items)} resultados em {elapsed}s")
        return items
    except Exception as e:
        elapsed = round(time.time() - start, 1)
        log.error(f"[Apify Cheerio] falhou após {elapsed}s: {e}")
        return []
