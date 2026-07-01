"""Scrapers de imobiliário."""
from bs4 import BeautifulSoup
from core.base_scraper import BaseScraper
from core.models import Listing
from core.normalize import parse_price, parse_area, clean_text
 
ZONE_SLUGS = {
    "Lisboa Centro": "lisboa",
    "Parque das Nações": "lisboa/parque-das-nacoes",
    "Alvalade": "lisboa/alvalade",
    "Alcântara": "lisboa/alcantara",
    "Cascais": "cascais",
    "Estoril": "cascais/estoril",
    "Porto Centro": "porto",
    "Almada": "almada",
    "Oeiras": "oeiras",
    "Sintra": "sintra",
}
 
 
class ImovirtualScraper(BaseScraper):
    portal_name = "Imovirtual"
    category = "imovel"
    render_js = True  # React/Next.js
 
    def build_search_urls(self, zones):
        return [f"https://www.imovirtual.com/comprar/apartamento/{ZONE_SLUGS.get(z, z.lower().replace(' ','-'))}/" for z in zones]
 
    def parse_listings(self, html, source_url):
        soup = BeautifulSoup(html, "html.parser")
        listings = []
        cards = soup.select("article[data-cy='listing-item']") or soup.select("article")
        zone_guess = source_url.split("/")[-2] if "/" in source_url else None
        for card in cards:
            title_el = card.select_one("p[data-cy='listing-item-title']") or card.select_one("h2") or card.select_one("a")
            link_el = card.select_one("a[href]")
            price_el = card.select_one("span[data-cy='listing-item-price']") or card.select_one("[class*='price']")
            area_el = card.select_one("[aria-label*='area']") or card.select_one("[class*='area']")
            title = clean_text(title_el.get_text()) if title_el else ""
            href = link_el["href"] if link_el and link_el.get("href") else ""
            url = href if href.startswith("http") else f"https://www.imovirtual.com{href}"
            price = parse_price(price_el.get_text()) if price_el else None
            area = parse_area(area_el.get_text()) if area_el else None
            if not title or not url:
                continue
            listings.append(Listing(
                portal=self.portal_name, category=self.category, external_id=url,
                title=title, price=price, market_estimate=None, currency="EUR",
                url=url, zone=zone_guess, area_m2=area, details={"fonte_raw": "imovirtual"},
            ))
        return listings
 
 
class CasaSapoScraper(BaseScraper):
    portal_name = "Casa Sapo"
    category = "imovel"
    render_js = True  # Angular
 
    def build_search_urls(self, zones):
        return [f"https://casa.sapo.pt/comprar-apartamentos/{ZONE_SLUGS.get(z, z.lower().replace(' ','-'))}/" for z in zones]
 
    def parse_listings(self, html, source_url):
        soup = BeautifulSoup(html, "html.parser")
        listings = []
        for card in soup.select("div.property-list-item") or soup.select("article"):
            title_el = card.select_one(".property-title") or card.select_one("h2")
            link_el = card.select_one("a[href]")
            price_el = card.select_one(".property-price") or card.select_one("[class*='price']")
            area_el = card.select_one("[class*='area']")
            title = clean_text(title_el.get_text()) if title_el else ""
            href = link_el["href"] if link_el and link_el.get("href") else ""
            url = href if href.startswith("http") else f"https://casa.sapo.pt{href}"
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
 
 
class IdealistaScraper(BaseScraper):
    portal_name = "Idealista"
    category = "imovel"
    render_js = True  # JS pesado + DataDome
 
    def build_search_urls(self, zones):
        return [f"https://www.idealista.pt/comprar-casas/{ZONE_SLUGS.get(z, z.lower().replace(' ','-'))}/" for z in zones]
 
    def parse_listings(self, html, source_url):
        soup = BeautifulSoup(html, "html.parser")
        listings = []
        for card in soup.select("article.item") or soup.select("article"):
            title_el = card.select_one("a.item-link")
            price_el = card.select_one(".item-price")
            details_el = card.select_one(".item-detail-char")
            title = clean_text(title_el.get("title", "") or title_el.get_text()) if title_el else ""
            href = title_el["href"] if title_el and title_el.get("href") else ""
            url = href if href.startswith("http") else f"https://www.idealista.pt{href}"
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
 
 
class CustoJustoScraper(BaseScraper):
    portal_name = "Custo Justo"
    category = "imovel"
    render_js = False  # HTML simples — 5 créditos
 
    def build_search_urls(self, zones):
        return [f"https://www.custojusto.pt/{ZONE_SLUGS.get(z, z.lower().replace(' ','-'))}/imobiliario" for z in zones]
 
    def parse_listings(self, html, source_url):
        soup = BeautifulSoup(html, "html.parser")
        listings = []
        for card in soup.select("article") or soup.select(".item-ad"):
            title_el = card.select_one("h2") or card.select_one("a")
            link_el = card.select_one("a[href]")
            price_el = card.select_one("[class*='price']")
            title = clean_text(title_el.get_text()) if title_el else ""
            href = link_el["href"] if link_el and link_el.get("href") else ""
            url = href if href.startswith("http") else f"https://www.custojusto.pt{href}"
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
    render_js = False  # HTML servidor — 5 créditos
 
    def build_search_urls(self, zones):
        return ["https://www.properstar.pt/portugal/comprar/apartamento"]
 
    def parse_listings(self, html, source_url):
        soup = BeautifulSoup(html, "html.parser")
        listings = []
        for card in soup.select("[data-test='listing-card']") or soup.select("article"):
            title_el = card.select_one("h2") or card.select_one("[class*='title']")
            link_el = card.select_one("a[href]")
            price_el = card.select_one("[class*='price']")
            area_el = card.select_one("[class*='surface']")
            title = clean_text(title_el.get_text()) if title_el else ""
            href = link_el["href"] if link_el and link_el.get("href") else ""
            url = href if href.startswith("http") else f"https://www.properstar.pt{href}"
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
    render_js = False  # Agregador estático — 5 créditos
 
    def build_search_urls(self, zones):
        return [f"https://www.mitula.pt/imoveis/{ZONE_SLUGS.get(z, z.lower().replace(' ','-'))}" for z in zones]
 
    def parse_listings(self, html, source_url):
        soup = BeautifulSoup(html, "html.parser")
        listings = []
        for card in soup.select("article") or soup.select(".item"):
            title_el = card.select_one("h2") or card.select_one("a")
            link_el = card.select_one("a[href]")
            price_el = card.select_one("[class*='price']")
            title = clean_text(title_el.get_text()) if title_el else ""
            href = link_el["href"] if link_el and link_el.get("href") else ""
            url = href if href.startswith("http") else f"https://www.mitula.pt{href}"
            price = parse_price(price_el.get_text()) if price_el else None
            if not title or not url:
                continue
            listings.append(Listing(
                portal=self.portal_name, category=self.category, external_id=url,
                title=title, price=price, market_estimate=None, currency="EUR",
                url=url, details={"fonte_raw": "mitula"},
            ))
        return listings
 
