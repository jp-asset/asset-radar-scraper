"""
Scrapers que usam actors prontos do Apify marketplace.
Zero manutenção de seletores — os autores dos actors mantêm-nos actualizados.
"""
import logging
from core.apify_client import run_actor, MAX_RESULTS_PER_SOURCE
from core.models import Listing
from core.normalize import parse_price, parse_area, clean_text
from core.config import ZONE_PRICES_DEFAULT

log = logging.getLogger("asset_radar")


class ImovirtualActorScraper:
    """Actor: solidcode/imovirtual-scraper — $2,50/1K resultados."""
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
                "transaction": "comprar",
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
                        "andar": item.get("floor", ""),
                        "agencia": item.get("agency", {}).get("name", "") if isinstance(item.get("agency"), dict) else "",
                        "fonte_raw": "imovirtual_actor",
                    },
                ))
        return listings


class IdealistaActorScraper:
    """Actor: lukass/idealista-scraper — $0,50–$3/1K resultados."""
    portal_name = "Idealista"
    category = "imovel"
    actor_id = "lukass/idealista-scraper"

    def run(self, zones: list[str]) -> list[Listing]:
        items = run_actor(self.actor_id, {
            "country": "pt",
            "operation": "sale",
            "propertyType": "homes",
            "locationName": "Lisboa",
            "maxResults": MAX_RESULTS_PER_SOURCE,
        })
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
                details={"tipologia": item.get("rooms", ""), "fonte_raw": "idealista_actor"},
            ))
        return listings


class OLXActorScraper:
    """Actor: piotrv1001/olx-listings-scraper — OLX Portugal."""
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
    """Actor: 3x1t/autoscout24-scraper — AutoScout24."""
    portal_name = "AutoScout24"
    category = "carro"
    actor_id = "3x1t/autoscout24-scraper"

    def run(self, zones: list[str]) -> list[Listing]:
        items = run_actor(self.actor_id, {
            "startUrls": [{"url": "https://www.autoscout24.pt/lst?sort=price&desc=0&ustate=N%2CU&size=20"}],
            "maxItems": MAX_RESULTS_PER_SOURCE,
        })
        listings = []
        for item in items:
            price = parse_price(item.get("price"))
            url = item.get("url", "")
            title = clean_text(item.get("title") or item.get("name", ""))
            if not url or not title:
                continue
            listings.append(Listing(
                portal=self.portal_name, category=self.category,
                external_id=url, title=title, price=price,
                market_estimate=price * 1.15 if price else None,
                currency="EUR", url=url,
                details={
                    "km": item.get("mileage", ""),
                    "ano": item.get("year", ""),
                    "fonte_raw": "autoscout24_actor",
                },
            ))
        return listings


class Chrono24ActorScraper:
    """Actor: memo23/chrono24-scraper — $3/1K resultados, 35+ campos."""
    portal_name = "Chrono24"
    category = "relogio"
    actor_id = "memo23/chrono24-scraper"

    def run(self, zones: list[str]) -> list[Listing]:
        items = run_actor(self.actor_id, {
            "startUrls": [{"url": "https://www.chrono24.pt/rolex/index.htm"}],
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
                    "ano": item.get("year", ""),
                    "estado": item.get("condition", ""),
                    "fonte_raw": "chrono24_actor",
                },
            ))
        return listings


class CatawikiActorScraper:
    """Actor: solidcode/catawiki-scraper — $2,50/1K resultados."""
    portal_name = "Catawiki"
    category = "arte"
    actor_id = "solidcode/catawiki-scraper"

    def run(self, zones: list[str]) -> list[Listing]:
        items = run_actor(self.actor_id, {
            "startUrls": [{"url": "https://www.catawiki.com/en/c/249-art"}],
            "maxItems": MAX_RESULTS_PER_SOURCE,
        })
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
                details={"tipo": "leilão", "fim_leilao": item.get("endTime", ""), "fonte_raw": "catawiki_actor"},
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
