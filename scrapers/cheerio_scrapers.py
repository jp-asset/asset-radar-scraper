   """
Scrapers manuais via Cheerio Scraper genérico do Apify.
Apenas compute units (~$0,05/50 páginas) — sem fee de actor.
Precisam de calibração de seletores quando os sites mudam o HTML.

Fontes: Casa Sapo, Custo Justo, Properstar, Mitula,
        Mobile.de, AutoUncle, Watchfinder, JoliCloset
"""
import logging
from core.apify_client import run_cheerio_scraper, MAX_RESULTS_PER_SOURCE
from core.models import Listing
from core.normalize import parse_price, parse_area, clean_text
from core.config import ZONE_PRICES_DEFAULT

log = logging.getLogger("asset_radar")

CASASAPO_JS = """
async function pageFunction(context) {
    const { $ } = context;
    const listings = [];
    $('div.property-list-item, article').each((i, el) => {
        const title = $(el).find('.property-title, h2').first().text().trim();
        const priceText = $(el).find('.property-price, [class*="price"]').first().text().trim();
        const href = $(el).find('a[href]').first().attr('href') || '';
        const url = href.startsWith('http') ? href : 'https://casa.sapo.pt' + href;
        const areaText = $(el).find('[class*="area"]').first().text().trim();
        if (title && url) {
            listings.push({ title, priceText, url, areaText, portal: 'Casa Sapo', category: 'imovel' });
        }
    });
    return listings;
}
"""

CUSTOJUSTO_JS = """
async function pageFunction(context) {
    const { $ } = context;
    const listings = [];
    $('article, .item-ad').each((i, el) => {
        const title = $(el).find('h2, a').first().text().trim();
        const priceText = $(el).find('[class*="price"]').first().text().trim();
        const href = $(el).find('a[href]').first().attr('href') || '';
        const url = href.startsWith('http') ? href : 'https://www.custojusto.pt' + href;
        if (title && url) {
            listings.push({ title, priceText, url, portal: 'Custo Justo', category: 'imovel' });
        }
    });
    return listings;
}
"""

PROPERSTAR_JS = """
async function pageFunction(context) {
    const { $ } = context;
    const listings = [];
    $('[data-test="listing-card"], article').each((i, el) => {
        const title = $(el).find('h2, [class*="title"]').first().text().trim();
        const priceText = $(el).find('[class*="price"]').first().text().trim();
        const areaText = $(el).find('[class*="surface"]').first().text().trim();
        const href = $(el).find('a[href]').first().attr('href') || '';
        const url = href.startsWith('http') ? href : 'https://www.properstar.pt' + href;
        if (title && url) {
            listings.push({ title, priceText, areaText, url, portal: 'Properstar', category: 'imovel' });
        }
    });
    return listings;
}
"""

MITULA_JS = """
async function pageFunction(context) {
    const { $ } = context;
    const listings = [];
    $('article, .item').each((i, el) => {
        const title = $(el).find('h2, a').first().text().trim();
        const priceText = $(el).find('[class*="price"]').first().text().trim();
        const href = $(el).find('a[href]').first().attr('href') || '';
        const url = href.startsWith('http') ? href : 'https://www.mitula.pt' + href;
        if (title && url) {
            listings.push({ title, priceText, url, portal: 'Mitula', category: 'imovel' });
        }
    });
    return listings;
}
"""

MOBILEDE_JS = """
async function pageFunction(context) {
    const { $ } = context;
    const listings = [];
    $('[data-testid="result-item"], article').each((i, el) => {
        const title = $(el).find('h2, [class*="title"]').first().text().trim();
        const priceText = $(el).find('[class*="price"]').first().text().trim();
        const href = $(el).find('a[href]').first().attr('href') || '';
        const url = href.startsWith('http') ? href : 'https://www.mobile.de' + href;
        if (title && url) {
            listings.push({ title, priceText, url, portal: 'Mobile.de', category: 'carro' });
        }
    });
    return listings;
}
"""

AUTOUNCLE_JS = """
async function pageFunction(context) {
    const { $ } = context;
    const listings = [];
    $('[class*="car-listing"], article').each((i, el) => {
        const title = $(el).find('h2, [class*="title"]').first().text().trim();
        const priceText = $(el).find('[class*="price"]').first().text().trim();
        const href = $(el).find('a[href]').first().attr('href') || '';
        const url = href.startsWith('http') ? href : 'https://www.autouncle.pt' + href;
        if (title && url) {
            listings.push({ title, priceText, url, portal: 'AutoUncle', category: 'carro' });
        }
    });
    return listings;
}
"""

WATCHFINDER_JS = """
async function pageFunction(context) {
    const { $ } = context;
    const listings = [];
    $('[class*="product-tile"], article').each((i, el) => {
        const title = $(el).find('h3, [class*="title"]').first().text().trim();
        const priceText = $(el).find('[class*="price"]').first().text().trim();
        const href = $(el).find('a[href]').first().attr('href') || '';
        const url = href.startsWith('http') ? href : 'https://www.watchfinder.com' + href;
        if (title && url) {
            listings.push({ title, priceText, url, portal: 'Watchfinder', category: 'relogio' });
        }
    });
    return listings;
}
"""

JOLICLOSET_JS = """
async function pageFunction(context) {
    const { $ } = context;
    const listings = [];
    $('[data-testid="product-card"], article').each((i, el) => {
        const title = $(el).find('h3, [class*="title"]').first().text().trim();
        const priceText = $(el).find('[class*="price"]').first().text().trim();
        const href = $(el).find('a[href]').first().attr('href') || '';
        const url = href.startsWith('http') ? href : 'https://www.jolicloset.com' + href;
        if (title && url) {
            listings.push({ title, priceText, url, portal: 'JoliCloset', category: 'moda' });
        }
    });
    return listings;
}
"""


def items_to_listings(items: list[dict], default_zone: str = None) -> list[Listing]:
    """Converte resultados do Cheerio Scraper para Listings normalizados."""
    listings = []
    for item in items:
        if not isinstance(item, dict):
            continue
        url = item.get("url", "")
        title = clean_text(item.get("title", ""))
        price = parse_price(item.get("priceText", ""))
        area = parse_area(item.get("areaText", ""))
        portal = item.get("portal", "Desconhecido")
        category = item.get("category", "geral")
        zone = item.get("zone") or default_zone
        ppm2 = ZONE_PRICES_DEFAULT.get(zone, 5000) if zone else None
        market = ppm2 * area if (ppm2 and area) else (price * 1.15 if price else None)
        if not url or not title:
            continue
        listings.append(Listing(
            portal=portal, category=category,
            external_id=url, title=title, price=price,
            market_estimate=market, currency="EUR", url=url,
            zone=zone, area_m2=area,
            details={"fonte_raw": f"{portal.lower().replace(' ', '_')}_cheerio"},
        ))
    return listings


CHEERIO_SOURCES = [
    ("Casa Sapo", ["https://casa.sapo.pt/comprar-apartamentos/lisboa/"], CASASAPO_JS, "Lisboa Centro"),
    ("Custo Justo", ["https://www.custojusto.pt/lisboa-centro/imobiliario"], CUSTOJUSTO_JS, "Lisboa Centro"),
    ("Properstar", ["https://www.properstar.pt/portugal/comprar/apartamento"], PROPERSTAR_JS, None),
    ("Mitula", ["https://www.mitula.pt/imoveis/lisboa-centro"], MITULA_JS, "Lisboa Centro"),
    ("Mobile.de", ["https://www.mobile.de/pt/carro/lisboa"], MOBILEDE_JS, None),
    ("AutoUncle", ["https://www.autouncle.pt/pt/carros_usados"], AUTOUNCLE_JS, None),
    ("Watchfinder", ["https://www.watchfinder.com/watches"], WATCHFINDER_JS, None),
    ("JoliCloset", ["https://www.jolicloset.com/pt/bolsas"], JOLICLOSET_JS, None),
]


def run_all_cheerio() -> list[tuple[str, list[Listing]]]:
    """Corre o Cheerio Scraper para todas as 8 fontes manuais."""
    results = []
    for name, urls, js, zone in CHEERIO_SOURCES:
        log.info(f"[Cheerio] A correr {name}...")
        items = run_cheerio_scraper(urls, js)
        listings = items_to_listings(items, default_zone=zone)
        log.info(f"[Cheerio] {name}: {len(listings)} anúncios")
        results.append((name, listings))
    return results
