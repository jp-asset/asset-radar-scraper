"""
Asset Radar — Orquestrador principal do scan diário.

Estratégia de otimização de custo/recursos:
1. Corre primeiro TODOS os scrapers só com HttpClient (rápido, sem browser).
2. Só abre UM browser Playwright (reutilizado entre fontes) para as fontes que
   falharam com 'js_challenge' — em vez de abrir/fechar browser por fonte.
3. Fecha o browser assim que todas as fontes-fallback terminam.
4. Grava o resultado final num único ficheiro JSON, versionado no git.

Isto significa: o custo computacional caro (browser Chromium) só é pago
pelas fontes que realmente precisam, e só uma vez por scan (não por scraper).
"""
import json
import logging
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.http_client import HttpClient, BrowserClient, fetch_with_fallback
from core.config import ZONE_PRICES_DEFAULT
from core.models import Listing

from scrapers.imovirtual import ImovirtualScraper
from scrapers.casasapo import CasaSapoScraper
from scrapers.idealista import IdealistaScraper
from scrapers.autoscout24 import AutoScout24Scraper
from scrapers.chrono24 import Chrono24Scraper
from scrapers.catawiki import CatawikiScraper
from scrapers.jolicloset import JoliClosetScraper
from scrapers.imobiliario_secundario import CustoJustoScraper, ProperstarScraper, MitulaScraper
from scrapers.diversos import OLXScraper, WatchfinderScraper, MobileDeScraper, AutoUncleScraper

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("asset_radar")

ZONES = list(ZONE_PRICES_DEFAULT.keys())

ALL_SCRAPER_CLASSES = [
    ImovirtualScraper, CasaSapoScraper, IdealistaScraper,
    CustoJustoScraper, ProperstarScraper, MitulaScraper,
    OLXScraper, AutoScout24Scraper, MobileDeScraper, AutoUncleScraper,
    Chrono24Scraper, WatchfinderScraper,
    JoliClosetScraper, CatawikiScraper,
]

OUTPUT_PATH = os.environ.get("OUTPUT_PATH", "data/opportunities.json")


def compute_market_estimate(listing: Listing) -> None:
    """Preenche market_estimate para imóveis usando preço/m² de referência por zona."""
    if listing.category == "imovel" and listing.zone and listing.area_m2:
        ppm2 = ZONE_PRICES_DEFAULT.get(listing.zone)
        if ppm2:
            listing.market_estimate = ppm2 * listing.area_m2
    elif listing.price and not listing.market_estimate:
        # Para categorias sem zona (relógios, carros, arte, moda): estimativa conservadora
        listing.market_estimate = listing.price * 1.15


def run_full_scan() -> dict:
    started_at = datetime.now(timezone.utc)
    http_client = HttpClient()
    all_listings: list[Listing] = []
    source_stats = []

    # FASE 1 — todos os scrapers que NÃO precisam de browser (rápido, barato)
    log.info("=== FASE 1: scrapers HTTP simples ===")
    needs_browser_classes = []
    for cls in ALL_SCRAPER_CLASSES:
        if cls.needs_browser:
            needs_browser_classes.append(cls)
            continue
        scraper = cls(http_client=http_client, browser=None)
        try:
            results = scraper.run(ZONES)
            for l in results:
                compute_market_estimate(l)
                l.compute_score()
            all_listings.extend(results)
            source_stats.append({"portal": cls.portal_name, "found": len(results), "method": "http"})
            log.info(f"[{cls.portal_name}] {len(results)} anúncios (HTTP simples)")
        except Exception as e:
            log.error(f"[{cls.portal_name}] falhou: {e}")
            source_stats.append({"portal": cls.portal_name, "found": 0, "method": "http", "error": str(e)})

    # FASE 2 — scrapers que precisam de browser (mais caro — um browser só, reutilizado)
    log.info("=== FASE 2: scrapers com browser (Playwright) ===")
    if needs_browser_classes:
        try:
            with BrowserClient(headless=True) as browser:
                for cls in needs_browser_classes:
                    scraper = cls(http_client=http_client, browser=browser)
                    try:
                        results = scraper.run(ZONES)
                        for l in results:
                            compute_market_estimate(l)
                            l.compute_score()
                        all_listings.extend(results)
                        source_stats.append({"portal": cls.portal_name, "found": len(results), "method": "browser"})
                        log.info(f"[{cls.portal_name}] {len(results)} anúncios (browser)")
                    except Exception as e:
                        log.error(f"[{cls.portal_name}] falhou: {e}")
                        source_stats.append({"portal": cls.portal_name, "found": 0, "method": "browser", "error": str(e)})
        except Exception as e:
            log.error(f"Não foi possível iniciar o browser Playwright: {e}")
            for cls in needs_browser_classes:
                source_stats.append({"portal": cls.portal_name, "found": 0, "method": "browser", "error": "browser_unavailable"})

    finished_at = datetime.now(timezone.utc)
    duration_s = (finished_at - started_at).total_seconds()

    # Remove duplicados (mesma URL = mesmo anúncio)
    seen_urls = set()
    unique_listings = []
    for l in sorted(all_listings, key=lambda x: x.score, reverse=True):
        if l.url in seen_urls:
            continue
        seen_urls.add(l.url)
        unique_listings.append(l)

    output = {
        "scanned_at": started_at.isoformat(),
        "duration_seconds": round(duration_s, 1),
        "total_opportunities": len(unique_listings),
        "source_stats": source_stats,
        "opportunities": [l.to_dict() for l in unique_listings],
    }

    log.info(f"=== SCAN COMPLETO: {len(unique_listings)} oportunidades únicas em {duration_s:.1f}s ===")
    return output


def main():
    result = run_full_scan()
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    log.info(f"Resultado gravado em {OUTPUT_PATH}")

    # Resumo legível para os logs do GitHub Actions
    print("\n" + "=" * 60)
    print(f"SCAN DIÁRIO — {result['scanned_at']}")
    print(f"Total: {result['total_opportunities']} oportunidades")
    print("=" * 60)
    for s in result["source_stats"]:
        status = f"erro: {s['error']}" if s.get("error") else f"{s['found']} anúncios"
        print(f"  {s['portal']:25s} [{s['method']:7s}] {status}")
    print("=" * 60)


if __name__ == "__main__":
    main()
