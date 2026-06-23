"""Scraper Imovirtual — imobiliário."""
from bs4 import BeautifulSoup
from core.base_scraper import BaseScraper
from core.models import Listing
from core.normalize import parse_price, parse_area, clean_text
from core.config import ZONE_SLUGS

BASE_URL = "https://www.imovirtual.com"


class ImovirtualScraper(BaseScraper):
    portal_name = "Imovirtual"
    category = "imovel"
    needs_browser = True  # confirmado no diagnóstico: JS challenge

    def build_search_urls(self, zones: list[str]) -> list[str]:
        urls = []
        for zone in zones:
            slug = ZONE_SLUGS.get(zone, {}).get("imovirtual", zone.lower().replace(" ", "-"))
            urls.append(f"{BASE_URL}/comprar/apartamento/{slug}/")
        return urls

    def parse_listings(self, html: str, source_url: str) -> list[Listing]:
        soup = BeautifulSoup(html, "html.parser")
        listings = []
        # Seletores aproximados — a confirmar/ajustar contra o HTML real capturado em produção
        cards = soup.select("article[data-cy='listing-item']") or soup.select("article")

        zone_guess = source_url.split("/")[-2] if "/" in source_url else None

        for card in cards:
            title_el = card.select_one("p[data-cy='listing-item-title']") or card.select_one("h2") or card.select_one("a")
            link_el = card.select_one("a[href]")
            price_el = card.select_one("span[data-cy='listing-item-price']") or card.select_one("[class*='price']")
            area_el = card.select_one("[aria-label*='area']") or card.select_one("[class*='area']")

            title = clean_text(title_el.get_text()) if title_el else ""
            href = link_el["href"] if link_el and link_el.get("href") else ""
            url = href if href.startswith("http") else f"{BASE_URL}{href}"
            price = parse_price(price_el.get_text()) if price_el else None
            area = parse_area(area_el.get_text()) if area_el else None

            if not title or not url:
                continue

            listings.append(Listing(
                portal=self.portal_name,
                category=self.category,
                external_id=url,
                title=title or "Imóvel",
                price=price,
                market_estimate=None,  # calculado depois com ZONE_PRICES
                currency="EUR",
                url=url,
                zone=zone_guess,
                area_m2=area,
                details={"fonte_raw": "imovirtual"},
            ))
        return listings
