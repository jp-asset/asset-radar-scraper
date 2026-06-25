"""Scraper Idealista — imobiliário (alternativa ao API oficial, para uso enquanto não há aprovação)."""
from bs4 import BeautifulSoup
from core.base_scraper import BaseScraper
from core.models import Listing
from core.normalize import parse_price, parse_area, clean_text

BASE_URL = "https://www.idealista.pt"


class IdealistaScraper(BaseScraper):
    portal_name = "Idealista"
    category = "imovel"
    needs_browser = True  # confirmado no diagnóstico: bloqueio 403 direto, precisa de browser+stealth

    def build_search_urls(self, zones: list[str]) -> list[str]:
        urls = []
        for zone in zones:
            slug = zone.lower().replace(" ", "-")
            urls.append(f"{BASE_URL}/comprar-casas/{slug}/")
        return urls

    def parse_listings(self, html: str, source_url: str) -> list[Listing]:
        soup = BeautifulSoup(html, "html.parser")
        listings = []
        cards = soup.select("article.item") or soup.select("article")

        for card in cards:
            title_el = card.select_one("a.item-link")
            price_el = card.select_one(".item-price")
            details_el = card.select_one(".item-detail-char")

            title = clean_text(title_el.get("title", "") or title_el.get_text()) if title_el else ""
            href = title_el["href"] if title_el and title_el.get("href") else ""
            url = href if href.startswith("http") else f"{BASE_URL}{href}"
            price = parse_price(price_el.get_text()) if price_el else None
            area = parse_area(details_el.get_text()) if details_el else None

            if not title or not url:
                continue

            listings.append(Listing(
                portal=self.portal_name, category=self.category, external_id=url,
                title=title, price=price, market_estimate=None, currency="EUR",
                url=url, area_m2=area, details={"fonte_raw": "idealista"},
            ))
        return listings
