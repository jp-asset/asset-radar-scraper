"""Scrapers de automóveis, relógios, moda e arte."""
from bs4 import BeautifulSoup
from core.base_scraper import BaseScraper
from core.models import Listing
from core.normalize import parse_price, clean_text


class OLXScraper(BaseScraper):
    portal_name = "OLX"
    category = "geral"
    needs_browser = True
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


class AutoScout24Scraper(BaseScraper):
    portal_name = "AutoScout24"
    category = "carro"
    needs_browser = True
    BASE_URL = "https://www.autoscout24.pt"

    def build_search_urls(self, zones: list[str]) -> list[str]:
        return [f"{self.BASE_URL}/lst?sort=price&desc=0&ustate=N%2CU&size=20&page=1"]

    def parse_listings(self, html: str, source_url: str) -> list[Listing]:
        soup = BeautifulSoup(html, "html.parser")
        listings = []
        for card in soup.select("article[data-testid='list-item']") or soup.select("article"):
            title_el = card.select_one("h2") or card.select_one("a")
            link_el = card.select_one("a[href]")
            price_el = card.select_one("[data-testid='regular-price']") or card.select_one("[class*='price']")
            km_el = card.select_one("[data-testid='mileage_road']")
            year_el = card.select_one("[data-testid='first_registration']")
            title = clean_text(title_el.get_text()) if title_el else ""
            href = link_el["href"] if link_el and link_el.get("href") else ""
            url = href if href.startswith("http") else f"{self.BASE_URL}{href}"
            price = parse_price(price_el.get_text()) if price_el else None
            if not title or not url:
                continue
            listings.append(Listing(
                portal=self.portal_name, category=self.category, external_id=url,
                title=title, price=price, market_estimate=None, currency="EUR", url=url,
                details={"km": clean_text(km_el.get_text()) if km_el else None,
                         "ano": clean_text(year_el.get_text()) if year_el else None,
                         "fonte_raw": "autoscout24"},
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
    needs_browser = True
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


class Chrono24Scraper(BaseScraper):
    portal_name = "Chrono24"
    category = "relogio"
    needs_browser = True
    BASE_URL = "https://www.chrono24.pt"
    BRANDS = ["rolex", "patek-philippe", "audemars-piguet", "omega"]

    def build_search_urls(self, zones: list[str]) -> list[str]:
        return [f"{self.BASE_URL}/{b}/index.htm" for b in self.BRANDS]

    def parse_listings(self, html: str, source_url: str) -> list[Listing]:
        soup = BeautifulSoup(html, "html.parser")
        listings = []
        brand = source_url.split("/")[-2] if "/" in source_url else "relógio"
        for card in soup.select("a.article-item") or soup.select("[data-article-id]"):
            title_el = card.select_one(".article-title") or card
            price_el = card.select_one(".price")
            href = card.get("href", "")
            url = href if href.startswith("http") else f"{self.BASE_URL}{href}"
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


class WatchfinderScraper(BaseScraper):
    portal_name = "Watchfinder"
    category = "relogio"
    needs_browser = True
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


class JoliClosetScraper(BaseScraper):
    portal_name = "JoliCloset"
    category = "moda"
    needs_browser = True
    BASE_URL = "https://www.jolicloset.com"

    def build_search_urls(self, zones: list[str]) -> list[str]:
        return [f"{self.BASE_URL}/pt/bolsas", f"{self.BASE_URL}/pt/relogios"]

    def parse_listings(self, html: str, source_url: str) -> list[Listing]:
        soup = BeautifulSoup(html, "html.parser")
        listings = []
        for card in soup.select("[data-testid='product-card']") or soup.select("article"):
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
                url=url, details={"fonte_raw": "jolicloset"},
            ))
        return listings


class CatawikiScraper(BaseScraper):
    portal_name = "Catawiki"
    category = "arte"
    needs_browser = True
    BASE_URL = "https://www.catawiki.com"

    def build_search_urls(self, zones: list[str]) -> list[str]:
        return [f"{self.BASE_URL}/en/c/249-art", f"{self.BASE_URL}/en/c/49-watches"]

    def parse_listings(self, html: str, source_url: str) -> list[Listing]:
        soup = BeautifulSoup(html, "html.parser")
        listings = []
        for card in soup.select("[data-testid='lot-card']") or soup.select("article"):
            title_el = card.select_one("h3") or card.select_one("a")
            link_el = card.select_one("a[href]")
            price_el = card.select_one("[class*='bid']") or card.select_one("[class*='price']")
            title = clean_text(title_el.get_text()) if title_el else ""
            href = link_el["href"] if link_el and link_el.get("href") else ""
            url = href if href.startswith("http") else f"{self.BASE_URL}{href}"
            price = parse_price(price_el.get_text()) if price_el else None
            if not title or not url:
                continue
            listings.append(Listing(
                portal=self.portal_name, category=self.category, external_id=url,
                title=title, price=price, market_estimate=None, currency="EUR",
                url=url, details={"fonte_raw": "catawiki", "tipo": "leilão"},
            ))
        return listings
