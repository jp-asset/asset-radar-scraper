"""
Scrapers que usam actors prontos do Apify marketplace.
Zero manutencao de seletores — os autores dos actors mantem-nos actualizados.

NOTA: run_actor() usa client.run(run.id).dataset() — compativel com apify-client 3.x
"""
import logging
import time
from datetime import timedelta
from core.apify_client import get_apify_client, MAX_RESULTS_PER_SOURCE
from core.models import Listing
from core.normalize import parse_price, parse_area, clean_text
from core.config import ZONE_PRICES_DEFAULT

log = logging.getLogger("asset_radar")


def run_actor(actor_id: str, run_input: dict, timeout_secs: int = 180) -> list[dict]:
    """
    Corre um actor do Apify e devolve os resultados como lista de dicts.
    Usa client.run(run.id).dataset() — forma correcta no apify-client 3.x.
    O objeto devolvido por actor.call() e um Run, nao um dict.
    """
    client = get_apify_client()
    log.info(f"[Apify] A correr actor {actor_id} (max {MAX_RESULTS_PER_SOURCE} resultados)")
    start = time.time()
    try:
        run = client.actor(actor_id).call(
            run_input=run_input,
            memory_mbytes=256,
            wait_duration=timedelta(seconds=timeout_secs),
        )
        if run is None:
            log.warning(f"[Apify] {actor_id}: run devolveu None (timeout?)")
            return []
        elapsed = round(time.time() - start, 1)
        items = list(client.run(run.id).dataset().iterate_items())
        log.info(f"[Apify] {actor_id}: {len(items)} resultados em {elapsed}s")
        return items
    except Exception as e:
        elapsed = round(time.time() - start, 1)
        log.error(f"[Apify] {actor_id} falhou apos {elapsed}s: {e}")
        return []


class ImovirtualActorScraper:
    """Actor: solidcode/imovirtual-scraper"""
    portal_name = "Imovirtual"
    category = "imovel"
    actor_id = "solidcode/imovirtual-scraper"

    def run(self, zones: list[str]) -> list[Listing]:
        listings = []
        for zone in zones[:2]:
            slug = {"Lisboa Centro": "lisboa", "Porto Centro": "porto",
                    "Cascais": "cascais"}.get(zone, "lisboa")
            items = run_actor(self.actor_id, {
                "location": slug,
                "transaction": "buy",
                "propertyType": "apartamento",
                "maxResults": MAX_RESULTS_PER_SOURCE,
            })
            for item in items:
                price = parse_price(item.get("price") or item.get("totalPrice"))
                area = parse_area(item.get("area") or item.get("livingArea"))
                url = item.get("url", "")
                title = clean_text(item.get("title") or f"Apartamento {zone}")
                if not url:
                    continue
                ppm2 = ZONE_PRICES_DEFAULT.get(zone, 5000)
                market = ppm2 * area if area else None
                listings.append(Listing(
                    portal=self.portal_name, category=self.category,
                    external_id=url, title=title, price=price,
                    market_estimate=market, currency="EUR", url=url,
                    zone=zone, area_m2=area,
                    posted_date=item.get("dateCreated"),
                    details={
                        "tipologia": item.get("rooms", ""),
                        "casas_banho": item.get("bathrooms", ""),
                        "fonte_raw": "imovirtual_actor",
                    },
                ))
        return listings


class IdealistaActorScraper:
    """Actor: lukass/idealista-scraper"""
    portal_name = "Idealista"
    category = "imovel"
    actor_id = "lukass/idealista-scraper"

    def run(self, zones: list[str]) -> list[Listing]:
        items = run_actor(self.actor_id, {
            "country": "pt",
            "operation": "sale",
            "propertyType": "homes",
            "startUrls": [{"url": "https://www.idealista.pt/comprar-casas/lisboa/"}],
            "maxResults": MAX_RESULTS_PER_SOURCE,
        }, timeout_secs=240)
        listings = []
        for item in items:
            price = parse_price(item.get("price"))
            area = parse_area(item.get("size"))
            url = item.get("url", "")
            title = clean_text(item.get("title") or item.get("description", "")[:60])
            if not url:
                continue
            zone = item.get("district") or item.get("neighborhood") or "Lisboa"
            ppm2 = ZONE_PRICES_DEFAULT.get(zone, 5000)
            market = ppm2 * area if area else None
            listings.append(Listing(
                portal=self.portal_name, category=self.category,
                external_id=url, title=title, price=price,
                market_estimate=market, currency="EUR", url=url,
                zone=zone, area_m2=area,
                details={"fonte_raw": "idealista_actor"},
            ))
        return listings


class OLXActorScraper:
    """Actor: piotrv1001/olx-listings-scraper"""
    portal_name = "OLX"
    category = "geral"
    actor_id = "piotrv1001/olx-listings-scraper"

    def run(self, zones: list[str]) -> list[Listing]:
        items = run_actor(self.actor_id, {
            "startUrls": [{"url": "https://www.olx.pt/imoveis/"}],
            "maxItems": MAX_RESULTS_PER_SOURCE,
            "country": "pt",
        })
        listings = []
        for item in items:
            price = parse_price(item.get("price"))
            url = item.get("url", "")
            title = clean_text(item.get("title", ""))
            if not url or not title:
                continue
            listings.append(Listing(
                portal=self.portal_name, category="imovel",
                external_id=url, title=title, price=price,
                market_estimate=price * 1.15 if price else None,
                currency="EUR", url=url,
                posted_date=item.get("createdAt"),
                details={"fonte_raw": "olx_actor"},
            ))
        return listings


class AutoScout24ActorScraper:
    """
    Actor: blackfalcondata/autoscout24-scraper
    Gratuito (so compute units) — substitui 3x1t que expirou.
    """
    portal_name = "AutoScout24"
    category = "carro"
    actor_id = "blackfalcondata/autoscout24-scraper"

    def run(self, zones: list[str]) -> list[Listing]:
        items = run_actor(self.actor_id, {
            "startUrls": [{"url": "https://www.autoscout24.pt/lst?sort=price&desc=0&ustate=N%2CU&size=20"}],
            "maxResults": MAX_RESULTS_PER_SOURCE,
        })
        listings = []
        for item in items:
            price = parse_price(item.get("price"))
            url = item.get("url") or item.get("portalUrl", "")
            title = clean_text(item.get("title") or item.get("name", ""))
            if not url or not title:
                continue
            listings.append(Listing(
                portal=self.portal_name, category=self.category,
                external_id=url, title=title, price=price,
                market_estimate=price * 1.15 if price else None,
                currency="EUR", url=url,
                details={
                    "km": str(item.get("mileage", "")),
                    "ano": str(item.get("year", "")),
                    "fonte_raw": "autoscout24_actor",
                },
            ))
        return listings


class Chrono24ActorScraper:
    """Actor: memo23/chrono24-scraper — usa .com nao .pt"""
    portal_name = "Chrono24"
    category = "relogio"
    actor_id = "memo23/chrono24-scraper"

    def run(self, zones: list[str]) -> list[Listing]:
        items = run_actor(self.actor_id, {
            "startUrls": [{"url": "https://www.chrono24.com/rolex/index.htm"}],
            "maxItems": MAX_RESULTS_PER_SOURCE,
        })
        listings = []
        for item in items:
            price = parse_price(item.get("price"))
            url = item.get("url", "")
            title = clean_text(item.get("title") or item.get("model", ""))
            if not url:
                continue
            listings.append(Listing(
                portal=self.portal_name, category=self.category,
                external_id=url, title=title, price=price,
                market_estimate=price * 1.15 if price else None,
                currency="EUR", url=url,
                details={
                    "marca": item.get("brand", ""),
                    "ref": item.get("reference", ""),
                    "ano": str(item.get("year", "")),
                    "fonte_raw": "chrono24_actor",
                },
            ))
        return listings


class CatawikiActorScraper:
    """Actor: solidcode/catawiki-scraper — usa keywords nao startUrls"""
    portal_name = "Catawiki"
    category = "arte"
    actor_id = "solidcode/catawiki-scraper"

    def run(self, zones: list[str]) -> list[Listing]:
        items = run_actor(self.actor_id, {
            "keywords": ["art", "painting", "sculpture"],
            "maxItems": MAX_RESULTS_PER_SOURCE,
        }, timeout_secs=240)
        listings = []
        for item in items:
            price = parse_price(item.get("currentBid") or item.get("price"))
            url = item.get("url", "")
            title = clean_text(item.get("title", ""))
            if not url or not title:
                continue
            listings.append(Listing(
                portal=self.portal_name, category=self.category,
                external_id=url, title=title, price=price,
                market_estimate=price * 1.15 if price else None,
                currency="EUR", url=url,
                details={"tipo": "leilao", "fonte_raw": "catawiki_actor"},
            ))
        return listings


ALL_ACTOR_SCRAPERS = [
    ImovirtualActorScraper,
    IdealistaActorScraper,
    OLXActorScraper,
    AutoScout24ActorScraper,
    Chrono24ActorScraper,
    CatawikiActorScraper,
]
