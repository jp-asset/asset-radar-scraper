"""
Asset Radar — Orquestrador principal do scan diário.

Arquitectura:
- 6 fontes via actors prontos Apify (Imovirtual, Idealista, OLX, AutoScout24, Chrono24, Catawiki)
- 8 fontes via HTTP + BeautifulSoup directamente no GitHub Actions (custo $0)
"""
import json
import logging
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.config import ZONE_PRICES_DEFAULT
from core.models import Listing
from scrapers.actor_scrapers import ALL_ACTOR_SCRAPERS
from scrapers.cheerio_scrapers import run_all_http_scrapers

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("asset_radar")

ZONES = list(ZONE_PRICES_DEFAULT.keys())
OUTPUT_PATH = os.environ.get("OUTPUT_PATH", "data/opportunities.json")


def compute_market_estimate(listing: Listing) -> None:
    if listing.category == "imovel" and listing.zone and listing.area_m2:
        ppm2 = ZONE_PRICES_DEFAULT.get(listing.zone)
        if ppm2 and not listing.market_estimate:
            listing.market_estimate = ppm2 * listing.area_m2
    if not listing.market_estimate and listing.price:
        listing.market_estimate = listing.price * 1.15


def run_full_scan() -> dict:
    started_at = datetime.now(timezone.utc)
    all_listings: list[Listing] = []
    source_stats = []

    log.info("=== FASE 1: Actors prontos do Apify marketplace ===")
    for cls in ALL_ACTOR_SCRAPERS:
        scraper = cls()
        try:
            results = scraper.run(ZONES)
            for l in results:
                compute_market_estimate(l)
                l.compute_score()
            all_listings.extend(results)
            source_stats.append({
                "portal": scraper.portal_name,
                "found": len(results),
                "method": "apify_actor",
            })
            log.info(f"[{scraper.portal_name}] {len(results)} anúncios (actor)")
        except Exception as e:
            log.error(f"[{scraper.portal_name}] falhou: {e}")
            source_stats.append({
                "portal": scraper.portal_name,
                "found": 0,
                "method": "apify_actor",
                "error": str(e),
            })

    log.info("=== FASE 2: HTTP directo (sem créditos Apify) ===")
    try:
        http_results = run_all_http_scrapers(ZONES)
        for portal_name, listings in http_results:
            for l in listings:
                compute_market_estimate(l)
                l.compute_score()
            all_listings.extend(listings)
            source_stats.append({
                "portal": portal_name,
                "found": len(listings),
                "method": "http_directo",
            })
    except Exception as e:
        log.error(f"HTTP scrapers falharam: {e}")

    finished_at = datetime.now(timezone.utc)
    duration_s = (finished_at - started_at).total_seconds()

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

    log.info(f"=== SCAN COMPLETO: {len(unique_listings)} oportunidades em {duration_s:.1f}s ===")
    return output


def main():
    result = run_full_scan()
    os.makedirs(os.path.dirname(OUTPUT_PATH) if os.path.dirname(OUTPUT_PATH) else ".", exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    log.info(f"Resultado gravado em {OUTPUT_PATH}")

    print("\n" + "=" * 60)
    print(f"SCAN DIÁRIO — {result['scanned_at']}")
    print(f"Total: {result['total_opportunities']} oportunidades")
    print("=" * 60)
    for s in result["source_stats"]:
        status = f"erro: {s['error']}" if s.get("error") else f"{s['found']} anúncios"
        print(f"  {s['portal']:20s} [{s['method']:15s}] {status}")
    print("=" * 60)


if __name__ == "__main__":
    main()
