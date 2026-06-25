"""Scraper Casa Sapo — imobiliário."""
from bs4 import BeautifulSoup
from core.base_scraper import BaseScraper
from core.models import Listing
from core.normalize import parse_price, parse_area, clean_text

BASE_URL = "https://casa.sapo.pt"


class CasaSapoScraper(BaseScraper):
    portal_name = "Casa Sapo"
    category = "imovel"
    needs_browser = True  # confirmado no diagnóstico: JS challenge

    def build_search_urls(self, zones: list[str]) -> list[str]:
        urls = []
        for zone in zones:
            slug = zone.lower().replace(" ", "-")
            urls.append(f"{BASE_URL}/comprar-apartamentos/{slug}/")
        return urls

    def parse_listings(self, html: str, source_url: str) -> list[Listing]:
        soup = BeautifulSoup(html, "html.parser")
        listings = []
        cards = soup.select("div.property-list-item") or soup.select("article")

        for card in cards:
            title_el = card.select_one(".property-title") or card.select_one("h2")
            link_el = card.select_one("a[href]")
            price_el = card.select_one(".property-price") or card.select_one("[class*='price']")
            area_el = card.select_one("[class*='area']")

            title = clean_text(title_el.get_text()) if title_el else ""
            href = link_el["href"] if link_el and link_el.get("href") else ""
            url = href if href.startswith("http") else f"{BASE_URL}{href}"
            price = parse_price(price_el.get_text()) if price_el else None
            area = parse_area(area_el.get_text()) if area_el else None

            if not title or not url:
                continue

            listings.append(Listing(
                portal=self.portal_name, category=self.category, external_id=url,
                title=title, price=price, market_estimate=None, currency="EUR",
                url=url, area_m2=area, details={"fonte_raw": "casasapo"},
            ))
        return listings
