"""
Scrapers manuais via HTTP + BeautifulSoup — 8 fontes secundárias.
Correm directamente no GitHub Actions, sem usar créditos do Apify.
Custo: $0 (só tempo de execução do workflow, que é gratuito).

Nota: estas fontes são mais simples e não precisam de anti-bot avançado.
Se começarem a bloquear, migrar para actors Apify específicos.
"""
import time
import random
import logging
import requests
from bs4 import BeautifulSoup
from core.models import Listing
from core.normalize import parse_price, parse_area, clean_text
from core.config import ZONE_PRICES_DEFAULT

log = logging.getLogger("asset_radar")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-PT,pt;q=0.9,en;q=0.8",
}


def fetch_html(url: str) -> str:
    time.sleep(random.uniform(1.5, 3.0))
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        return resp.text
    except Exception as e:
        log.warning(f"[HTTP] falhou em {url}: {e}")
        return ""


def scrape_casa_sapo(zones: list[str]) -> list[Listing]:
    listings = []
    for zone in zones[:2]:
        slug = {"Lisboa Centro": "lisboa", "Porto Centro": "porto", "Cascais": "cascais"}.get(zone, "lisboa")
        html = fetch_html(f"https://casa.sapo.pt/comprar-apartamentos/{slug}/")
        if not html:
            continue
        soup = BeautifulSoup(html, "html.parser")
        for card in (soup.select("div.property-list-item") or soup.select("article"))[:20]:
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
            ppm2 = ZONE_PRICES_DEFAULT.get(zone, 5000)
            market = ppm2 * area if area else None
            listings.append(Listing(
                portal="Casa Sapo", category="imovel", external_id=url,
                title=title, price=price, market_estimate=market,
                currency="EUR", url=url, zone=zone, area_m2=area,
                details={"fonte_raw": "casasapo_http"},
            ))
    log.info(f"[Casa Sapo] {len(listings)} anúncios")
    return listings


def scrape_custo_justo(zones: list[str]) -> list[Listing]:
    listings = []
    for zone in zones[:2]:
        slug = {"Lisboa Centro": "lisboa-centro", "Porto Centro": "porto"}.get(zone, "lisboa")
        html = fetch_html(f"https://www.custojusto.pt/{slug}/imobiliario")
        if not html:
            continue
        soup = BeautifulSoup(html, "html.parser")
        for card in (soup.select("article") or soup.select(".item-ad"))[:20]:
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
                portal="Custo Justo", category="imovel", external_id=url,
                title=title, price=price, market_estimate=price * 1.15 if price else None,
                currency="EUR", url=url, zone=zone,
                details={"fonte_raw": "custojusto_http"},
            ))
    log.info(f"[Custo Justo] {len(listings)} anúncios")
    return listings


def scrape_properstar() -> list[Listing]:
    listings = []
    html = fetch_html("https://www.properstar.pt/portugal/comprar/apartamento")
    if not html:
        return listings
    soup = BeautifulSoup(html, "html.parser")
    for card in (soup.select("[data-test='listing-card']") or soup.select("article"))[:20]:
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
            portal="Properstar", category="imovel", external_id=url,
            title=title, price=price, market_estimate=price * 1.15 if price else None,
            currency="EUR", url=url, area_m2=area,
            details={"fonte_raw": "properstar_http"},
        ))
    log.info(f"[Properstar] {len(listings)} anúncios")
    return listings


def scrape_mitula(zones: list[str]) -> list[Listing]:
    listings = []
    for zone in zones[:2]:
        slug = {"Lisboa Centro": "lisboa-centro", "Porto Centro": "porto"}.get(zone, "lisboa")
        html = fetch_html(f"https://www.mitula.pt/imoveis/{slug}")
        if not html:
            continue
        soup = BeautifulSoup(html, "html.parser")
        for card in (soup.select("article") or soup.select(".item"))[:20]:
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
                portal="Mitula", category="imovel", external_id=url,
                title=title, price=price, market_estimate=price * 1.15 if price else None,
                currency="EUR", url=url, zone=zone,
                details={"fonte_raw": "mitula_http"},
            ))
    log.info(f"[Mitula] {len(listings)} anúncios")
    return listings


def scrape_mobilede() -> list[Listing]:
    listings = []
    html = fetch_html("https://www.mobile.de/pt/carro/lisboa")
    if not html:
        return listings
    soup = BeautifulSoup(html, "html.parser")
    for card in (soup.select("[data-testid='result-item']") or soup.select("article"))[:20]:
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
            portal="Mobile.de", category="carro", external_id=url,
            title=title, price=price, market_estimate=price * 1.15 if price else None,
            currency="EUR", url=url,
            details={"fonte_raw": "mobilede_http"},
        ))
    log.info(f"[Mobile.de] {len(listings)} anúncios")
    return listings


def scrape_autouncle() -> list[Listing]:
    listings = []
    html = fetch_html("https://www.autouncle.pt/pt/carros_usados")
    if not html:
        return listings
    soup = BeautifulSoup(html, "html.parser")
    for card in (soup.select("[class*='car-listing']") or soup.select("article"))[:20]:
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
            portal="AutoUncle", category="carro", external_id=url,
            title=title, price=price, market_estimate=price * 1.15 if price else None,
            currency="EUR", url=url,
            details={"fonte_raw": "autouncle_http"},
        ))
    log.info(f"[AutoUncle] {len(listings)} anúncios")
    return listings


def scrape_watchfinder() -> list[Listing]:
    listings = []
    html = fetch_html("https://www.watchfinder.com/watches")
    if not html:
        return listings
    soup = BeautifulSoup(html, "html.parser")
    for card in (soup.select("[class*='product-tile']") or soup.select("article"))[:20]:
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
            portal="Watchfinder", category="relogio", external_id=url,
            title=title, price=price, market_estimate=price * 1.15 if price else None,
            currency="EUR", url=url,
            details={"fonte_raw": "watchfinder_http"},
        ))
    log.info(f"[Watchfinder] {len(listings)} anúncios")
    return listings


def scrape_jolicloset() -> list[Listing]:
    listings = []
    html = fetch_html("https://www.jolicloset.com/pt/bolsas")
    if not html:
        return listings
    soup = BeautifulSoup(html, "html.parser")
    for card in (soup.select("[data-testid='product-card']") or soup.select("article"))[:20]:
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
            portal="JoliCloset", category="moda", external_id=url,
            title=title, price=price, market_estimate=price * 1.15 if price else None,
            currency="EUR", url=url,
            details={"fonte_raw": "jolicloset_http"},
        ))
    log.info(f"[JoliCloset] {len(listings)} anúncios")
    return listings


def run_all_http_scrapers(zones: list[str]) -> list[tuple[str, list[Listing]]]:
    """Corre todos os scrapers HTTP para as 8 fontes manuais."""
    results = []
    results.append(("Casa Sapo", scrape_casa_sapo(zones)))
    results.append(("Custo Justo", scrape_custo_justo(zones)))
    results.append(("Properstar", scrape_properstar()))
    results.append(("Mitula", scrape_mitula(zones)))
    results.append(("Mobile.de", scrape_mobilede()))
    results.append(("AutoUncle", scrape_autouncle()))
    results.append(("Watchfinder", scrape_watchfinder()))
    results.append(("JoliCloset", scrape_jolicloset()))
    return results
