"""Scrapers para OLX, Watchfinder, Mobile.de e AutoUncle."""
from bs4 import BeautifulSoup
from core.base_scraper import BaseScraper
from core.models import Listing
from core.normalize import parse_price, clean_text


class OLXScraper(BaseScraper):
    portal_name = "OLX"
    category = "geral"
    needs_browser = True  # confirmado no diagnóstico: JS challenge
    BASE_URL = "https://www.olx.pt"

    def build_search_urls(self, zones: list[str]) -> list[str]:
        return [f"{self.BASE_URL}/imoveis/", f"{self.BASE_URL}/carros-motos-e-barcos/carros/"]

    def parse_listings(self, html: str, source_url: str) -> list[Listing]:
        soup = BeautifulSoup(html, "html.parser")
        listings = []
        cat = "imovel" if "imoveis" in source_url else "carro"
        for card in soup.select("[data-cy='l-card']") or soup.select("article"):
            title_el = card.select_one("h6") or card.select_one("h4")
            link_el = card.select_one("a[href]")
            price_el = card.select_one("[data-testid='ad-price']")
            title = clean_text(title_el.get_text()) if title_el else ""
            href = link_el["href"] if link_el and link_el.get("href") else ""
            url = href if href.startswith("http") else f"{self.BASE_URL}{href}"
            price = parse_price(price_el.get_text()) if price_el else None
            if not title or not url:
                continue
            listings.append(Listing(
                portal=self.portal_name, category=cat, external_id=url,
                title=title, price=price, market_estimate=None, currency="EUR",
                url=url, details={"fonte_raw": "olx"},
            ))
        return listings


class WatchfinderScraper(BaseScraper):
    portal_name = "Watchfinder"
    category = "relogio"
    needs_browser = True  # confirmado no diagnóstico: JS challenge
    BASE_URL = "https://www.watchfinder.com"

    def build_search_urls(self, zones: list[str]) -> list[str]:
        return [f"{self.BASE_URL}/watches"]

    def parse_listings(self, html: str, source_url: str) -> list[Listing]:
        soup = BeautifulSoup(html, "html.parser")
        listings = []
        for card in soup.select("[class*='product-tile']") or soup.select("article"):
            title_el = card.select_one("h3") or card.select_one("[class*='title']")
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
                url=url, details={"fonte_raw": "watchfinder"},
            ))
        return listings


class MobileDeScraper(BaseScraper):
    portal_name = "Mobile.de"
    category = "carro"
    needs_browser = True
    BASE_URL = "https://www.mobile.de"

    def build_search_urls(self, zones: list[str]) -> list[str]:
        return [f"{self.BASE_URL}/pt/carro/lisboa"]

    def parse_listings(self, html: str, source_url: str) -> list[Listing]:
        soup = BeautifulSoup(html, "html.parser")
        listings = []
        for card in soup.select("[data-testid='result-item']") or soup.select("article"):
            title_el = card.select_one("h2") or card.select_one("[class*='title']")
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
                url=url, details={"fonte_raw": "mobilede"},
            ))
        return listings


class AutoUncleScraper(BaseScraper):
    portal_name = "AutoUncle"
    category = "carro"
    needs_browser = False  # tenta HTTP simples primeiro
    BASE_URL = "https://www.autouncle.pt"

    def build_search_urls(self, zones: list[str]) -> list[str]:
        return [f"{self.BASE_URL}/pt/carros_usados"]

    def parse_listings(self, html: str, source_url: str) -> list[Listing]:
        soup = BeautifulSoup(html, "html.parser")
        listings = []
        for card in soup.select("[class*='car-listing']") or soup.select("article"):
            title_el = card.select_one("h2") or card.select_one("[class*='title']")
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
                url=url, details={"fonte_raw": "autouncle"},
            ))
        return listings
