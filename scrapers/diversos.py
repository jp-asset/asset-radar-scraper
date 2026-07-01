"""Scrapers de automóveis, relógios, moda e arte."""
from bs4 import BeautifulSoup
from core.base_scraper import BaseScraper
from core.models import Listing
from core.normalize import parse_price, clean_text
 
 
class OLXScraper(BaseScraper):
    portal_name = "OLX"
    category = "geral"
    render_js = True  # React
 
    def build_search_urls(self, zones):
        return ["https://www.olx.pt/imoveis/", "https://www.olx.pt/carros-motos-e-barcos/carros/"]
 
    def parse_listings(self, html, source_url):
        soup = BeautifulSoup(html, "html.parser")
        listings = []
        cat = "imovel" if "imoveis" in source_url else "carro"
        for card in soup.select("[data-cy='l-card']") or soup.select("article"):
            title_el = card.select_one("h6") or card.select_one("h4")
            link_el = card.select_one("a[href]")
            price_el = card.select_one("[data-testid='ad-price']")
            title = clean_text(title_el.get_text()) if title_el else ""
            href = link_el["href"] if link_el and link_el.get("href") else ""
            url = href if href.startswith("http") else f"https://www.olx.pt{href}"
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
    render_js = True  # Vue.js
 
    def build_search_urls(self, zones):
        return ["https://www.autoscout24.pt/lst?sort=price&desc=0&ustate=N%2CU&size=20&page=1"]
 
    def parse_listings(self, html, source_url):
        soup = BeautifulSoup(html, "html.parser")
        listings = []
        for card in soup.select("article[data-testid='list-item']") or soup.select("article"):
            title_el = card.select_one("h2") or card.select_one("a")
            link_el = card.select_one("a[href]")
            price_el = card.select_one("[data-testid='regular-price']") or card.select_one("[class*='price']")
            title = clean_text(title_el.get_text()) if title_el else ""
            href = link_el["href"] if link_el and link_el.get("href") else ""
            url = href if href.startswith("http") else f"https://www.autoscout24.pt{href}"
            price = parse_price(price_el.get_text()) if price_el else None
            if not title or not url:
                continue
            listings.append(Listing(
                portal=self.portal_name, category=self.category, external_id=url,
                title=title, price=price, market_estimate=None, currency="EUR",
                url=url, details={"fonte_raw": "autoscout24"},
            ))
        return listings
 
 
class MobileDeScraper(BaseScraper):
    portal_name = "Mobile.de"
    category = "carro"
    render_js = True  # JS pesado
 
    def build_search_urls(self, zones):
        return ["https://www.mobile.de/pt/carro/lisboa"]
 
    def parse_listings(self, html, source_url):
        soup = BeautifulSoup(html, "html.parser")
        listings = []
        for card in soup.select("[data-testid='result-item']") or soup.select("article"):
            title_el = card.select_one("h2") or card.select_one("[class*='title']")
            link_el = card.select_one("a[href]")
            price_el = card.select_one("[class*='price']")
            title = clean_text(title_el.get_text()) if title_el else ""
            href = link_el["href"] if link_el and link_el.get("href") else ""
            url = href if href.startswith("http") else f"https://www.mobile.de{href}"
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
    render_js = False  # HTML simples — 5 créditos
 
    def build_search_urls(self, zones):
        return ["https://www.autouncle.pt/pt/carros_usados"]
 
    def parse_listings(self, html, source_url):
        soup = BeautifulSoup(html, "html.parser")
        listings = []
        for card in soup.select("[class*='car-listing']") or soup.select("article"):
            title_el = card.select_one("h2") or card.select_one("[class*='title']")
            link_el = card.select_one("a[href]")
            price_el = card.select_one("[class*='price']")
            title = clean_text(title_el.get_text()) if title_el else ""
            href = link_el["href"] if link_el and link_el.get("href") else ""
            url = href if href.startswith("http") else f"https://www.autouncle.pt{href}"
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
    render_js = False  # HTML servidor — 5 créditos
    BRANDS = ["rolex", "patek-philippe", "audemars-piguet", "omega"]
 
    def build_search_urls(self, zones):
        return [f"https://www.chrono24.pt/{b}/index.htm" for b in self.BRANDS]
 
    def parse_listings(self, html, source_url):
        soup = BeautifulSoup(html, "html.parser")
        listings = []
        brand = source_url.split("/")[-2] if "/" in source_url else "relógio"
        for card in soup.select("a.article-item") or soup.select("[data-article-id]"):
            title_el = card.select_one(".article-title") or card
            price_el = card.select_one(".price")
            href = card.get("href", "")
            url = href if href.startswith("http") else f"https://www.chrono24.pt{href}"
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
    render_js = False  # HTML servidor — 5 créditos
 
    def build_search_urls(self, zones):
        return ["https://www.watchfinder.com/watches"]
 
    def parse_listings(self, html, source_url):
        soup = BeautifulSoup(html, "html.parser")
        listings = []
        for card in soup.select("[class*='product-tile']") or soup.select("article"):
            title_el = card.select_one("h3") or card.select_one("[class*='title']")
            link_el = card.select_one("a[href]")
            price_el = card.select_one("[class*='price']")
            title = clean_text(title_el.get_text()) if title_el else ""
            href = link_el["href"] if link_el and link_el.get("href") else ""
            url = href if href.startswith("http") else f"https://www.watchfinder.com{href}"
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
    render_js = True  # React
 
    def build_search_urls(self, zones):
        return ["https://www.jolicloset.com/pt/bolsas", "https://www.jolicloset.com/pt/relogios"]
 
    def parse_listings(self, html, source_url):
        soup = BeautifulSoup(html, "html.parser")
        listings = []
        for card in soup.select("[data-testid='product-card']") or soup.select("article"):
            title_el = card.select_one("h3") or card.select_one("[class*='title']")
            link_el = card.select_one("a[href]")
            price_el = card.select_one("[class*='price']")
            title = clean_text(title_el.get_text()) if title_el else ""
            href = link_el["href"] if link_el and link_el.get("href") else ""
            url = href if href.startswith("http") else f"https://www.jolicloset.com{href}"
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
    render_js = True  # React/GraphQL
 
    def build_search_urls(self, zones):
        return ["https://www.catawiki.com/en/c/249-art", "https://www.catawiki.com/en/c/49-watches"]
 
    def parse_listings(self, html, source_url):
        soup = BeautifulSoup(html, "html.parser")
        listings = []
        for card in soup.select("[data-testid='lot-card']") or soup.select("article"):
            title_el = card.select_one("h3") or card.select_one("a")
            link_el = card.select_one("a[href]")
            price_el = card.select_one("[class*='bid']") or card.select_one("[class*='price']")
            title = clean_text(title_el.get_text()) if title_el else ""
            href = link_el["href"] if link_el and link_el.get("href") else ""
            url = href if href.startswith("http") else f"https://www.catawiki.com{href}"
            price = parse_price(price_el.get_text()) if price_el else None
            if not title or not url:
                continue
            listings.append(Listing(
                portal=self.portal_name, category=self.category, external_id=url,
                title=title, price=price, market_estimate=None, currency="EUR",
                url=url, details={"fonte_raw": "catawiki", "tipo": "leilão"},
            ))
        return listings
