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

log = logging.getLogger("asset_radar")

MAX_RESULTS_PER_SOURCE = int(os.environ.get("MAX_RESULTS_PER_SOURCE", "50"))


def get_apify_client():
    from apify_client import ApifyClient
    api_key = os.environ.get("APIFY_API_KEY", "")
    if not api_key:
        raise ValueError(
            "APIFY_API_KEY não definida. "
            "Adiciona como Secret no GitHub: Settings → Secrets → Actions → APIFY_API_KEY"
        )
    return ApifyClient(api_key)

# NOTA (17/08/2026): existiam aqui duas funções `run_actor` / `run_cheerio_scraper`
# não utilizadas por nenhum scraper (mortas — grep confirmou zero chamadas) e que
# ainda tinham o bug antigo `run.get("defaultDatasetId")`, incompatível com
# apify-client 3.x. Removidas para não serem copiadas por engano no futuro.
# A implementação correcta e em uso vive em scrapers/actor_scrapers.py::run_actor
# (usa client.run(run.id).dataset() — confirmado compatível com 3.x).
