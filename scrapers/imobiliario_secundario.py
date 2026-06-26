"""Scrapers para Custo Justo, Properstar e Mitula — imobiliário secundário."""
from bs4 import BeautifulSoup
from core.base_scraper import BaseScraper
from core.models import Listing
from core.normalize import parse_price, parse_area, clean_text


class CustoJustoScraper(BaseScraper):
    portal_name = "Custo Justo"
    category = "imovel"
    needs_browser = True  # confirmado no diagnóstico: JS challenge
    BASE_URL = "https://www.custojusto.pt"

    def build_search_urls(self, zones: list[str]) -> list[str]:
        return [f"{self.BASE_URL}/{z.lower().replace(' ', '-')}/imobiliario" for z in zones]

    def parse_listings(self, html: str, source_url: str) -> list[Listing]:
        soup = BeautifulSoup(html, "html.parser")
        listings = []
        for card in soup.select("article") or soup.select(".item-ad"):
            title_el = card.select_one("h2") or card.select_one("a")
            link_el = card.select_one("a[href]")
            price_el = card.select_one("[class*='price']")
            title = clean_text(title_el.get_text()) if title_el else ""
            href = link_el["href"] if link_el and link_el.get("href") else ""
            url = href if href.startswith("http") else f"{self.BASE_URL}{href}"
            price = parse_price(price_el.get_text()) if price_el else None
            if not title or not url:
                continue
            listings.append(Listing(
                portal=self.portal_name, category=self.category, external_id=url,
                title=title, price=price, market_estimate=None, currency="EUR",
                url=url, details={"fonte_raw": "custojusto"},
            ))
        return listings


class ProperstarScraper(BaseScraper):
    portal_name = "Properstar"
    category = "imovel"
    needs_browser = True  # confirmado no diagnóstico: bloqueio 403/429
    BASE_URL = "https://www.properstar.pt"

    def build_search_urls(self, zones: list[str]) -> list[str]:
        return [f"{self.BASE_URL}/portugal/comprar/apartamento"]

    def parse_listings(self, html: str, source_url: str) -> list[Listing]:
        soup = BeautifulSoup(html, "html.parser")
        listings = []
        for card in soup.select("[data-test='listing-card']") or soup.select("article"):
            title_el = card.select_one("h2") or card.select_one("[class*='title']")
            link_el = card.select_one("a[href]")
            price_el = card.select_one("[class*='price']")
            area_el = card.select_one("[class*='surface']")
            title = clean_text(title_el.get_text()) if title_el else ""
            href = link_el["href"] if link_el and link_el.get("href") else ""
            url = href if href.startswith("http") else f"{self.BASE_URL}{href}"
            price = parse_price(price_el.get_text()) if price_el else None
            area = parse_area(area_el.get_text()) if area_el else None
            if not title or not url:
                continue
            listings.append(Listing(
                portal=self.portal_name, category=self.category, external_id=url,
                title=title, price=price, market_estimate=None, currency="EUR",
                url=url, area_m2=area, details={"fonte_raw": "properstar"},
            ))
        return listings


class MitulaScraper(BaseScraper):
    portal_name = "Mitula"
    category = "imovel"
    needs_browser = False  # agregador — tenta HTTP simples primeiro
    BASE_URL = "https://www.mitula.pt"

    def build_search_urls(self, zones: list[str]) -> list[str]:
        return [f"{self.BASE_URL}/imoveis/{z.lower().replace(' ', '-')}" for z in zones]

    def parse_listings(self, html: str, source_url: str) -> list[Listing]:
        soup = BeautifulSoup(html, "html.parser")
        listings = []
        for card in soup.select("article") or soup.select(".item"):
            title_el = card.select_one("h2") or card.select_one("a")
            link_el = card.select_one("a[href]")
            price_el = card.select_one("[class*='price']")
            title = clean_text(title_el.get_text()) if title_el else ""
            href = link_el["href"] if link_el and link_el.get("href") else ""
            url = href if href.startswith("http") else f"{self.BASE_URL}{href}"
            price = parse_price(price_el.get_text()) if price_el else None
            if not title or not url:
                continue
            listings.append(Listing(
                portal=self.portal_name, category=self.category, external_id=url,
                title=title, price=price, market_estimate=None, currency="EUR",
                url=url, details={"fonte_raw": "mitula"},
            ))
        return listings
