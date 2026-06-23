"""Scraper AutoScout24 — automóveis."""
from bs4 import BeautifulSoup
from core.base_scraper import BaseScraper
from core.models import Listing
from core.normalize import parse_price, clean_text

BASE_URL = "https://www.autoscout24.pt"


class AutoScout24Scraper(BaseScraper):
    portal_name = "AutoScout24"
    category = "carro"
    needs_browser = True  # confirmado no diagnóstico: timeout em HTTP simples, precisa de browser

    def build_search_urls(self, zones: list[str]) -> list[str]:
        # Automóveis não são filtrados por zona neste scraper — pesquisa nacional
        return [f"{BASE_URL}/lst?sort=price&desc=0&ustate=N%2CU&size=20&page=1"]

    def parse_listings(self, html: str, source_url: str) -> list[Listing]:
        soup = BeautifulSoup(html, "html.parser")
        listings = []
        cards = soup.select("article[data-testid='list-item']") or soup.select("article")

        for card in cards:
            title_el = card.select_one("h2") or card.select_one("a")
            link_el = card.select_one("a[href]")
            price_el = card.select_one("[data-testid='regular-price']") or card.select_one("[class*='price']")
            km_el = card.select_one("[data-testid='mileage_road']")
            year_el = card.select_one("[data-testid='first_registration']")

            title = clean_text(title_el.get_text()) if title_el else ""
            href = link_el["href"] if link_el and link_el.get("href") else ""
            url = href if href.startswith("http") else f"{BASE_URL}{href}"
            price = parse_price(price_el.get_text()) if price_el else None

            if not title or not url:
                continue

            listings.append(Listing(
                portal=self.portal_name, category=self.category, external_id=url,
                title=title, price=price, market_estimate=None, currency="EUR",
                url=url,
                details={
                    "km": clean_text(km_el.get_text()) if km_el else None,
                    "ano": clean_text(year_el.get_text()) if year_el else None,
                    "fonte_raw": "autoscout24",
                },
            ))
        return listings
