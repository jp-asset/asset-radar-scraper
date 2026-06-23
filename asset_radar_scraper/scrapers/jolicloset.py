"""Scraper JoliCloset — moda de luxo em segunda mão."""
from bs4 import BeautifulSoup
from core.base_scraper import BaseScraper
from core.models import Listing
from core.normalize import parse_price, clean_text

BASE_URL = "https://www.jolicloset.com"


class JoliClosetScraper(BaseScraper):
    portal_name = "JoliCloset"
    category = "moda"
    needs_browser = False  # diagnóstico não testou em profundidade — tenta HTTP primeiro

    def build_search_urls(self, zones: list[str]) -> list[str]:
        return [f"{BASE_URL}/pt/bolsas", f"{BASE_URL}/pt/relogios"]

    def parse_listings(self, html: str, source_url: str) -> list[Listing]:
        soup = BeautifulSoup(html, "html.parser")
        listings = []
        cards = soup.select("[data-testid='product-card']") or soup.select("article")

        for card in cards:
            title_el = card.select_one("h3") or card.select_one("[class*='title']")
            link_el = card.select_one("a[href]")
            price_el = card.select_one("[class*='price']")

            title = clean_text(title_el.get_text()) if title_el else ""
            href = link_el["href"] if link_el and link_el.get("href") else ""
            url = href if href.startswith("http") else f"{BASE_URL}{href}"
            price = parse_price(price_el.get_text()) if price_el else None

            if not title or not url:
                continue

            listings.append(Listing(
                portal=self.portal_name, category=self.category, external_id=url,
                title=title, price=price, market_estimate=None, currency="EUR",
                url=url, details={"fonte_raw": "jolicloset"},
            ))
        return listings
