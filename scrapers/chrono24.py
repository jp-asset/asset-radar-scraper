"""Scraper Chrono24 — relógios de luxo."""
from bs4 import BeautifulSoup
from core.base_scraper import BaseScraper
from core.models import Listing
from core.normalize import parse_price, clean_text

BASE_URL = "https://www.chrono24.pt"

BRANDS = ["rolex", "patek-philippe", "audemars-piguet", "omega"]


class Chrono24Scraper(BaseScraper):
    portal_name = "Chrono24"
    category = "relogio"
    needs_browser = True  # confirmado no diagnóstico: bloqueio 403/429

    def build_search_urls(self, zones: list[str]) -> list[str]:
        return [f"{BASE_URL}/{brand}/index.htm" for brand in BRANDS]

    def parse_listings(self, html: str, source_url: str) -> list[Listing]:
        soup = BeautifulSoup(html, "html.parser")
        listings = []
        cards = soup.select("a.article-item") or soup.select("[data-article-id]")
        brand = source_url.split("/")[-2] if "/" in source_url else "relógio"

        for card in cards:
            title_el = card.select_one(".article-title") or card
            price_el = card.select_one(".price")
            href = card.get("href", "")
            url = href if href.startswith("http") else f"{BASE_URL}{href}"
            title = clean_text(title_el.get_text()) if title_el else brand.title()
            price = parse_price(price_el.get_text()) if price_el else None

            if not url:
                continue

            listings.append(Listing(
                portal=self.portal_name, category=self.category, external_id=url,
                title=title, price=price, market_estimate=None, currency="EUR",
                url=url, details={"marca": brand.title(), "fonte_raw": "chrono24"},
            ))
        return listings
