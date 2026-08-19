"""
Scrapers manuais via HTTP + BeautifulSoup — 8 fontes secundárias.
Correm directamente no GitHub Actions, sem usar créditos do Apify.
Custo: $0 (só tempo de execução do workflow, que é gratuito).

Nota: estas fontes são mais simples e não precisam de anti-bot avançado.
Se começarem a bloquear, migrar para actors Apify específicos.

DIAGNÓSTICO 18/08/2026 — todas as 8 fontes devolviam sempre 0. Verifiquei
cada uma individualmente (URL real + se a página carrega dados sem
JavaScript). Resultado, por fonte:
  - Casa Sapo: URL estava certa, mas o robots.txt do site desautoriza TODOS
    os caminhos ("Disallow: /") — não é um bug de selector, é uma proibição
    explícita do site a qualquer scraping automático. Não contornamos
    robots.txt — fonte desactivada por omissão em config/sources.json
    (o código fica cá, mas não corre).
  - Custo Justo: URL errada (404) — corrigida.
  - Properstar: URL estava certa, mas dá HTTP 403 (bloqueio anti-bot/WAF) —
    mesmo resultado a partir de duas redes diferentes, o que sugere bloqueio
    a qualquer pedido automatizado, não só ao nosso. Desactivada por
    omissão; o código fica pronto para quando/se isso mudar.
  - Mitula: dá HTTP 401 mesmo na página inicial — bloqueio ao nível do
    site/CDN, não específico da nossa URL. Desactivada por omissão.
  - Mobile.de: URL errada (404) — corrigida para a página de pesquisa
    filtrada a "Portugal". Nota importante: mobile.de é um marketplace
    ALEMÃO — mesmo filtrado a "carros em Portugal", isto tende a devolver
    carros alemães à venda com entrega/localização em PT, não
    necessariamente vendedores portugueses. Mantido activo mas vale a pena
    reavaliar se faz sentido para o objectivo do projecto.
  - AutoUncle: URL errada (404) — corrigida.
  - Watchfinder: URL já estava certa e a página tem dados reais. Não
    consegui confirmar os nomes exactos das classes CSS (sem acesso de rede
    a partir deste ambiente para inspeccionar o HTML directamente) — os
    selectors foram alargados com mais alternativas de fallback, mas podem
    ainda precisar de afinação depois de correr uma vez a sério.
  - JoliCloset: URL errada (404) — o site não tem uma página genérica
    "/bolsas", está organizado por marca. Corrigida para uma página de
    marca real (Hermès bolsas) como fonte concreta.

DIAGNÓSTICO 18/08/2026 — RONDA 2 (depois de confirmar URLs, os selectors
ainda davam 0 em 4 das 5 fontes HTTP não-Casa-Sapo/Properstar/Mitula).
Desta vez fui buscar a estrutura HTML real (tags/classes literais), não só
confirmar que a URL existe:
  - Custo Justo: cada anúncio é um <a href="/.../imobiliario/apartamentos/
    {slug}-{id}"> que envolve o cartão inteiro — sem classes CSS a apoiarmo-
    nos. Título dentro em <h2>, preço em <h5>. Reescrito para seleccionar
    directamente por esse padrão de href.
  - AutoUncle: título é o próprio texto do <a href="/pt/d/{id}-usado-...">
    (não há um <h2>/<h3> à parte); o preço aparece como texto solto perto do
    link mas FORA dele (no contentor pai), ex. "€ 19.740". Reescrito para
    subir na árvore a partir do link até encontrar um preço.
  - JoliCloset: cartão é um <a> que envolve o produto inteiro, título num
    <h3> lá dentro, preço como texto solto no cartão — quando há desconto
    aparecem dois valores seguidos (ex. "2.600€ 2.340€"); usamos o último
    (mais baixo, o preço actual). Reescrito.
  - Mobile.de: consegui confirmar que a página TEM anúncios reais (ex. "BMW
    Z4 sDrive35i", "27.000 €"), mas não consegui obter tags/classes exactas
    a partir deste ambiente. Alarguei os selectors (mesma abordagem do
    Watchfinder), mas fica a nota honesta: mobile.de é fortemente React/JS,
    por isso mesmo com selectors correctos pode continuar a dar 0 se os
    cartões só existirem depois de JavaScript correr — nesse caso não é
    resolúvel via HTTP simples, só via browser headless (custo extra).
    [Desactivada por decisão do utilizador — ver config/sources.json.]

DIAGNÓSTICO 18/08/2026 — RONDA 3 (o log de diagnóstico da ronda 2 já deu a
resposta em vez de continuarmos a adivinhar às cegas): JoliCloset devolvia
status HTTP 403 — não é um problema de selectors nem de JavaScript, é um
bloqueio anti-bot (WAF) só nesta fonte (Custo Justo e AutoUncle, com os
mesmos headers básicos, deram 200 sem problema). Tentativa de correcção:
cabeçalhos HTTP muito mais completos e realistas (o conjunto que um Chrome
de secretária real envia — Accept-Encoding, Sec-Fetch-*, sec-ch-ua,
Upgrade-Insecure-Requests, Connection) mais um Referer a simular navegação
a partir da homepage do site, já que muitos WAFs tratam pedidos "directos"
a uma página profunda sem referer como tráfego automatizado. Se isto não
resolver, o próximo log vai voltar a mostrar status=403 e nesse caso já
não é resolúvel por cabeçalhos — teria de passar por Apify (custo) ou
browser headless.
"""
import time
import random
import re
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
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "pt-PT,pt;q=0.9,en;q=0.8",
    # NOTA 18/08/2026: NÃO incluir "br" (Brotli) aqui — foi a causa de uma
    # regressão real (log confirmado): ao anunciar suporte a Brotli sem o
    # pacote "brotli"/"brotlicffi" instalado (não está em requirements.txt),
    # sites que respondem com Content-Encoding: br fazem o requests/urllib3
    # devolver texto corrompido/truncado — os tamanhos de resposta caíram de
    # ~940KB para ~100KB no Custo Justo, por exemplo, e isso, não os
    # selectors, é que fez Custo Justo/AutoUncle/Watchfinder irem todos a 0
    # nesta mesma alteração. gzip/deflate já chegam, são suportados nativamente.
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "sec-ch-ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "DNT": "1",
}

# Padrão de preço em texto solto (fora de qualquer elemento com classe
# "price"), usado nas fontes onde o preço não está encapsulado (AutoUncle,
# JoliCloset) — apanha "€ 19.740", "2.600€" e também "540 000 €" (espaço
# normal ou insecável como separador de milhares).
#
# Corrigido 19/08/2026: confirmado com dados reais do scan (via GitHub) que
# a área já estava a ser extraída correctamente pela mesma técnica de subida
# no HTML, mas o preço continuava sempre a None — isso isola o problema no
# PADRÃO, não no alcance da busca. Custo Justo (e possivelmente outras
# fontes PT) usa espaço como separador de milhares no preço (ex.
# "540 000 €"), que o padrão antigo (só "." ou ",") não reconhecia. Ainda
# sem acesso de rede a partir deste ambiente para confirmar 100% a partir do
# HTML em bruto, mas é a explicação mais plausível dado que só a área falha.
_THOUSANDS_SEP = r"[ \t\xa0.,]"
PRICE_PATTERN = re.compile(
    rf"€\s?[\d]{{1,3}}(?:{_THOUSANDS_SEP}\d{{3}})*(?:[.,]\d+)?"
    rf"|[\d]{{1,3}}(?:{_THOUSANDS_SEP}\d{{3}})*(?:[.,]\d+)?\s?€"
)

# Igual ao PRICE_PATTERN mas também apanha $ e £ — adicionado 18/08/2026
# para o Watchfinder, que mostra preços em dólares (ex. "$7,085"), não em
# euros. Fontes portuguesas/europeias continuam a usar PRICE_PATTERN (só €)
# para não apanhar por engano outros números com formatação parecida.
#
# Nota: a variante "símbolo depois do número" NÃO permite espaço antes do
# símbolo (ex. "2.600€" apanha, "2016 €" não) — testado e confirmado que,
# sem esta restrição, texto como "... Year 2016 $7,085" apanhava "2016 $"
# em vez do preço real, porque um ano de 4 dígitos seguido de espaço e
# símbolo de moeda também batia certo com o padrão antigo. Isto mantém-se
# igual com a alteração 19/08/2026 (só o separador INTERNO dos grupos de
# milhares passou a aceitar espaço, não o espaço antes do símbolo).
PRICE_PATTERN_ANY = re.compile(
    rf"[€$£]\s?[\d]{{1,3}}(?:{_THOUSANDS_SEP}\d{{3}})*(?:[.,]\d+)?"
    rf"|[\d]{{1,3}}(?:{_THOUSANDS_SEP}\d{{3}})*(?:[.,]\d+)?[€$£]"
)

# Padrão de área (m²) em texto solto — usado nas fontes onde a área não
# está encapsulada num elemento próprio (mesmo caso do preço no Custo
# Justo/AutoUncle: aparece como texto solto num contentor pai do cartão).
AREA_PATTERN = re.compile(r"\d+[.,]?\d*\s*m[²2]\b", re.IGNORECASE)


def _find_in_ancestors(start_el, pattern: "re.Pattern", max_levels: int = 6) -> str | None:
    """
    Sobe na árvore a partir de `start_el` (inclusive) até `max_levels`
    contentores pai, à procura da primeira ocorrência de `pattern` no texto
    acumulado desse nível. Devolve o texto do match, ou None.

    Usado quando o dado (preço, área) não está dentro do próprio elemento
    do anúncio, mas nalgum contentor pai — caso confirmado em vários sites
    (Custo Justo, AutoUncle). Alargado de 3 para 6 níveis em 19/08/2026:
    3 níveis só cobria os casos mais simples e, sem acesso de rede a partir
    deste ambiente para confirmar a estrutura HTML actual do Custo Justo,
    alargar a busca é a correcção mais segura a fazer às cegas (não reduz
    precisão nos casos que já funcionavam, só aumenta o alcance).
    """
    el = start_el
    for _ in range(max_levels):
        if el is None:
            break
        match = pattern.search(el.get_text(separator=" "))
        if match:
            return match.group()
        el = el.find_parent()
    return None


def select_cards(soup: BeautifulSoup, selectors: list[str], limit: int = 20) -> list:
    """
    Tenta uma lista de selectors CSS por ordem e devolve o primeiro grupo
    não-vazio. Usado nas fontes onde não conseguimos confirmar a classe CSS
    exacta (sem acesso de rede a partir deste ambiente para inspeccionar o
    HTML real) — alarga as hipóteses em vez de depender de um único palpite.
    """
    for sel in selectors:
        found = soup.select(sel)
        if found:
            return found[:limit]
    return []


def fetch_html(url: str, referer: str | None = None, session: requests.Session | None = None) -> str:
    """
    `referer`: simula navegação a partir dessa página (em vez de um pedido
    "directo" a uma URL profunda) — alguns WAFs tratam a ausência de
    referer como sinal de bot. `session`: reutiliza cookies/conexão entre
    pedidos (ex. visitar a homepage antes da página de listagem), o que
    também se parece mais com um browser real do que pedidos isolados.
    """
    time.sleep(random.uniform(1.5, 3.0))
    headers = dict(HEADERS)
    if referer:
        headers["Referer"] = referer
    client = session or requests
    try:
        resp = client.get(url, headers=headers, timeout=15)
        # Log de diagnóstico: sem isto, um "0 anúncios" não distingue entre
        # "o pedido falhou/foi bloqueado" e "o pedido teve sucesso mas os
        # selectors não encontraram nada" — dois problemas muito diferentes.
        log.info(f"[HTTP] {url} -> status={resp.status_code}, {len(resp.text)} bytes")
        if resp.status_code != 200:
            log.warning(f"[HTTP] {url} devolveu status {resp.status_code} (possível bloqueio/anti-bot)")
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
    seen_hrefs = set()
    no_price_count = 0
    for zone in zones[:2]:
        slug = {"Lisboa Centro": "lisboa", "Porto Centro": "porto"}.get(zone, "lisboa")
        html = fetch_html(f"https://www.custojusto.pt/{slug}/imobiliario/apartamentos-venda")
        if not html:
            continue
        soup = BeautifulSoup(html, "html.parser")
        # Confirmado 18/08/2026: cada anúncio é o próprio <a href="/.../
        # imobiliario/apartamentos/{slug}-{id}"> — sem classes CSS por baixo.
        # Título em <h2> DENTRO do <a>.
        #
        # Corrigido 18/08/2026 ronda 4: confirmado por inspecção real que o
        # preço NÃO está dentro do <a> — está num elemento irmão a seguir ao
        # <a>, dentro do mesmo contentor pai. Subimos ao contentor pai e
        # procuramos o preço aí (não só dentro do link).
        #
        # Corrigido 19/08/2026: a app estava a mostrar estes anúncios sem
        # NENHUM dado (preço, área, score) — sinal de que o preço estava
        # sistematicamente a falhar (não só ocasionalmente). Sem acesso de
        # rede a custojusto.pt a partir deste ambiente para confirmar a
        # estrutura HTML actual, a correcção feita às cegas foi alargar o
        # alcance da busca (3 → 6 níveis de contentor pai, padrão € seguido
        # de padrão genérico como fallback) em vez de adivinhar uma classe
        # CSS nova. Também passámos a extrair a ÁREA (nunca tinha sido feito
        # aqui) e a usar o preço/m² de referência da zona para a estimativa
        # de mercado, em vez do heurístico fixo "+15%". Se isto não resolver,
        # o aviso [Custo Justo] no log do próximo scan real vai confirmar
        # que o problema é mesmo estrutural (a página pode ter passado a
        # carregar os cartões via JavaScript), não de alcance da busca.
        cards = soup.select("a[href*='/imobiliario/apartamentos/']")
        for card in cards[:20]:
            href = card.get("href", "")
            if not href or href in seen_hrefs:
                continue
            seen_hrefs.add(href)
            title_el = card.select_one("h2")
            title = clean_text(title_el.get_text()) if title_el else clean_text(card.get_text())
            url = href if href.startswith("http") else f"https://www.custojusto.pt{href}"

            price_text = _find_in_ancestors(card, PRICE_PATTERN, max_levels=6) \
                or _find_in_ancestors(card, PRICE_PATTERN_ANY, max_levels=6)
            price = parse_price(price_text) if price_text else None

            area_text = _find_in_ancestors(card, AREA_PATTERN, max_levels=6)
            area = parse_area(area_text) if area_text else None

            if not title or not url:
                continue

            # Estimativa de mercado: com área conhecida, usar o preço/m² de
            # referência da zona (mais real, consistente com o resto do
            # projecto); sem área, manter o heurístico antigo (+15%) como
            # fallback em vez de ficar sem estimativa nenhuma.
            ppm2 = ZONE_PRICES_DEFAULT.get(zone)
            if area and ppm2:
                market = ppm2 * area
            elif price:
                market = price * 1.15
            else:
                market = None

            if price is None:
                no_price_count += 1

            listings.append(Listing(
                portal="Custo Justo", category="imovel", external_id=url,
                title=title, price=price, market_estimate=market,
                currency="EUR", url=url, zone=zone, area_m2=area,
                details={"fonte_raw": "custojusto_http"},
            ))
    if listings and no_price_count == len(listings):
        log.warning(
            f"[Custo Justo] {no_price_count}/{len(listings)} anuncios SEM preco "
            "detectado mesmo subindo ate 6 niveis de contentor pai (padrao € e "
            "generico) - a estrutura HTML da pagina pode ter mudado desde a "
            "ultima confirmacao (18/08/2026). Precisa de inspeccao real no "
            "proximo log do GitHub Actions."
        )
    log.info(f"[Custo Justo] {len(listings)} anúncios ({len(listings) - no_price_count} com preço)")
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
    html = fetch_html("https://suchen.mobile.de/auto/portugal.html")
    if not html:
        return listings
    soup = BeautifulSoup(html, "html.parser")
    # Confirmei 18/08/2026 que a página TEM anúncios reais (ex. "BMW Z4
    # sDrive35i", "27.000 €"), mas não consegui obter as classes/tags HTML
    # exactas a partir deste ambiente — alarguei as hipóteses (mesma
    # abordagem do Watchfinder). Nota honesta: mobile.de é fortemente
    # React/JS — se os cartões só existirem depois de JavaScript correr,
    # isto continua a dar 0 e não é resolúvel via HTTP simples.
    cards = select_cards(soup, [
        "[data-testid='result-list-item']", "[data-testid='result-item']",
        "article[data-testid]", "[class*='result-item']",
        "article",
    ])
    for card in cards:
        title_el = card.select_one("h2") or card.select_one("[class*='title']") or card.select_one("[class*='name']")
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
    html = fetch_html("https://www.autouncle.pt/pt/carros-usados/em/Lisboa")
    if not html:
        return listings
    soup = BeautifulSoup(html, "html.parser")
    # Confirmado 18/08/2026: o título é o próprio texto do
    # <a href="/pt/d/{id}-usado-{ano}-{marca}-{modelo}">, não há <h2>/<h3> à
    # parte. O preço aparece como texto solto (ex. "€ 19.740") FORA do <a>,
    # no contentor pai — por isso subimos na árvore a partir do link.
    links = soup.select("a[href^='/pt/d/']")
    seen_hrefs = set()
    for link in links[:20]:
        href = link.get("href", "")
        if not href or href in seen_hrefs:
            continue
        seen_hrefs.add(href)
        title = clean_text(link.get_text())
        if not title:
            continue
        url = href if href.startswith("http") else f"https://www.autouncle.pt{href}"
        price = None
        parent = link.find_parent()
        for _ in range(3):
            if parent is None:
                break
            match = PRICE_PATTERN.search(parent.get_text(separator=" "))
            if match:
                price = parse_price(match.group())
                break
            parent = parent.find_parent()
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
    # Reescrito 18/08/2026 ronda 4: confirmado por inspecção real que a
    # página tem 26 relógios, cada um dentro de um <a href> simples, SEM
    # classe, data-testid ou tag semântica (article/li) distintiva — título
    # e preço são texto solto concatenado dentro do próprio <a> (ex.: "Omega
    # De Ville Ladymatic 425.32.34.20.55.002 ... $7,085"). As hipóteses de
    # selector CSS anteriores nunca apanhavam estes cartões reais — só
    # calhavam num <article> avulso nalgum outro sítio da página, dando
    # sempre ~1 resultado (o bug reportado). Nova abordagem: olhar
    # directamente para todos os <a href> e filtrar pelos que têm um preço
    # válido no próprio texto — mesma técnica já usada em JoliCloset/Artbid.
    # Nota: os preços aqui aparecem em USD ($), não em euros — por isso
    # usamos PRICE_PATTERN_ANY (não PRICE_PATTERN) e guardamos a moeda real.
    seen_hrefs = set()
    cards = [a for a in soup.find_all("a", href=True) if PRICE_PATTERN_ANY.search(a.get_text(separator=" "))]
    for card in cards[:30]:
        href = card.get("href", "")
        if not href or href in seen_hrefs:
            continue
        seen_hrefs.add(href)
        text = card.get_text(separator=" ")
        match = PRICE_PATTERN_ANY.search(text)
        if not match:
            continue
        price_raw = match.group()
        price = parse_price(price_raw)
        currency = "USD" if "$" in price_raw else ("GBP" if "£" in price_raw else "EUR")
        title = clean_text(text[:match.start()]) or clean_text(text)
        url = href if href.startswith("http") else f"https://www.watchfinder.com{href}"
        if not title or not url or not price:
            continue
        listings.append(Listing(
            portal="Watchfinder", category="relogio", external_id=url,
            title=title, price=price, market_estimate=price * 1.15 if price else None,
            currency=currency, url=url,
            details={"fonte_raw": "watchfinder_http"},
        ))
    log.info(f"[Watchfinder] {len(listings)} anúncios")
    return listings


def scrape_jolicloset() -> list[Listing]:
    listings = []
    # Não existe página genérica "/bolsas" (dava 404) — o site organiza por
    # marca. Usamos uma página de marca concreta e popular como fonte fixa.
    #
    # 18/08/2026 ronda 3: esta página devolvia status 403 (bloqueio anti-bot),
    # confirmado pelo log de diagnóstico — não era um problema de selectors.
    # Correcção tentada: usar uma sessão (cookies persistem entre pedidos,
    # tal como um browser real) e visitar primeiro a homepage, depois a
    # página de listagem com Referer=homepage — simula navegação humana em
    # vez de um pedido "directo" e isolado a uma URL profunda.
    session = requests.Session()
    fetch_html("https://www.jolicloset.com/pt/", session=session)  # "visita" à homepage, define cookies
    html = fetch_html(
        "https://www.jolicloset.com/pt/marcas-feminino/hermes/bolsas-femininas/bolsas",
        referer="https://www.jolicloset.com/pt/",
        session=session,
    )
    if not html:
        return listings
    soup = BeautifulSoup(html, "html.parser")
    # Confirmado 18/08/2026: o cartão é o próprio <a> que envolve o produto
    # inteiro, com o título num <h3> lá dentro; o preço é texto solto no
    # cartão — quando há desconto aparecem dois valores seguidos (ex.
    # "2.600€ 2.340€" = preço original + preço actual), usamos o último
    # (mais baixo). Filtramos por "tem um <h3> lá dentro" em vez de depender
    # de uma classe CSS específica, que não conseguimos confirmar.
    cards = [a for a in soup.find_all("a", href=True) if a.select_one("h3")]
    if not cards:
        # Diagnóstico: se isto aparecer no log, o pedido teve sucesso (ver
        # log "[HTTP] ... status=200") mas a estrutura HTML real recebida
        # não bate certo com o que confirmámos por WebFetch — sinal de que
        # a grelha de produtos só existe depois de JavaScript correr (React/
        # Next.js client-side rendering), o que o WebFetch pode ter
        # renderizado mas um pedido HTTP simples (requests) não consegue.
        total_a = len(soup.find_all("a"))
        total_h3 = len(soup.find_all("h3"))
        log.warning(
            f"[JoliCloset] 0 cartões encontrados — página tinha {total_a} <a> "
            f"e {total_h3} <h3> no total. Se {total_h3}==0, a grelha de "
            "produtos provavelmente só é gerada por JavaScript e não é "
            "visível num pedido HTTP simples (possível caso a resolver só "
            "com browser headless, não com requests+BeautifulSoup)."
        )
    seen_hrefs = set()
    for card in cards[:20]:
        href = card.get("href", "")
        if not href or href in seen_hrefs:
            continue
        seen_hrefs.add(href)
        title_el = card.select_one("h3")
        title = clean_text(title_el.get_text()) if title_el else ""
        url = href if href.startswith("http") else f"https://www.jolicloset.com{href}"
        prices_found = PRICE_PATTERN.findall(card.get_text(separator=" "))
        price = parse_price(prices_found[-1]) if prices_found else None
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


def scrape_standvirtual() -> list[Listing]:
    """
    Adicionada 18/08/2026. Confirmado por WebFetch: robots.txt sem bloqueio
    a listagens, e a página devolve anúncios reais no HTML inicial — título
    em <h2>, preço em <h3>, ambos dentro do <a href=".../carros/anuncio/...">.
    Standvirtual é OLX Group (mesma empresa-mãe da OLX que já usamos via
    Apify), mas este scraper corre por HTTP directo, sem créditos.
    """
    listings = []
    html = fetch_html("https://www.standvirtual.com/carros")
    if not html:
        return listings
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select("a[href*='/carros/anuncio/']")
    if not cards:
        log.warning(f"[Standvirtual] 0 cartões encontrados (ver [HTTP] acima para status/tamanho da resposta)")
    seen_hrefs = set()
    for card in cards[:20]:
        href = card.get("href", "")
        if not href or href in seen_hrefs:
            continue
        seen_hrefs.add(href)
        title_el = card.select_one("h2")
        title = clean_text(title_el.get_text()) if title_el else ""
        if not title:
            continue
        url = href if href.startswith("http") else f"https://www.standvirtual.com{href}"
        price_el = card.select_one("h3")
        price = parse_price(price_el.get_text()) if price_el else None
        if price is None:
            # fallback: preço pode estar fora do <a>, tal como no AutoUncle
            parent = card.find_parent()
            for _ in range(3):
                if parent is None:
                    break
                match = PRICE_PATTERN.search(parent.get_text(separator=" "))
                if match:
                    price = parse_price(match.group())
                    break
                parent = parent.find_parent()
        listings.append(Listing(
            portal="Standvirtual", category="carro", external_id=url,
            title=title, price=price, market_estimate=price * 1.15 if price else None,
            currency="EUR", url=url,
            details={"fonte_raw": "standvirtual_http"},
        ))
    log.info(f"[Standvirtual] {len(listings)} anúncios")
    return listings


def scrape_onebid() -> list[Listing]:
    """
    Adicionada 18/08/2026 a pedido explícito, apesar de confiança BAIXA:
    confirmado por WebFetch que esta página lista LEILÕES inteiros (ex.
    "56. Leilão de Obras de Arte", padrão de href
    /pt/auction/-/{ID} ou /pt/live/{ID}), não lotes individuais com preço —
    o valor de licitação de cada lote só carrega dentro da página do leilão,
    provavelmente via JavaScript. Por isso os resultados aqui não têm preço
    fiável (score vai ficar a 0) — servem para ver que leilões estão a
    decorrer, não para detectar "boas compras" sozinhos. Reavaliar se vale a
    pena manter activa depois de ver o primeiro log real.
    """
    listings = []
    html = fetch_html("https://onebid.pt/pt/auctions/Arte")
    if not html:
        return listings
    soup = BeautifulSoup(html, "html.parser")
    # Os leilões reais têm o texto do link a começar por um número (ex.
    # "56. Leilão de Obras de Arte", "114.º Leilão..."), ao contrário dos
    # links genéricos de navegação/menu — filtro simples para reduzir ruído.
    cards = [
        a for a in soup.select("a[href*='/auction/'], a[href*='/live/']")
        if re.match(r"^\d+", clean_text(a.get_text()))
    ]
    if not cards:
        log.warning("[Onebid] 0 leilões encontrados com o padrão esperado — ver [HTTP] acima para status/tamanho da resposta.")
    seen_hrefs = set()
    for card in cards[:20]:
        href = card.get("href", "")
        title = clean_text(card.get_text())
        if not href or not title or href in seen_hrefs:
            continue
        seen_hrefs.add(href)
        url = href if href.startswith("http") else f"https://onebid.pt{href}"
        price = None
        parent = card.find_parent()
        if parent:
            match = PRICE_PATTERN.search(parent.get_text(separator=" "))
            if match:
                price = parse_price(match.group())
        listings.append(Listing(
            portal="Onebid", category="arte", external_id=url,
            title=title, price=price, market_estimate=price * 1.15 if price else None,
            currency="EUR", url=url,
            details={"fonte_raw": "onebid_http"},
        ))
    if listings and not any(l.price for l in listings):
        log.warning(
            "[Onebid] leilões encontrados mas SEM preço em nenhum — confirma "
            "a suspeita de que a licitação actual só carrega via JavaScript."
        )
    log.info(f"[Onebid] {len(listings)} anúncios")
    return listings


def scrape_artbid() -> list[Listing]:
    """
    Adicionada 18/08/2026 a pedido explícito, apesar de confiança MUITO
    BAIXA: verifiquei 3 páginas diferentes (homepage, /en/categories,
    /en/lots — a página "todos os lotes") e nenhuma mostra lotes reais no
    HTML inicial, só estrutura/navegação — os lotes carregam via
    JavaScript. É bem provável que isto dê sempre 0 até resolvermos com
    browser headless ou API oficial. Código incluído mesmo assim, com
    diagnóstico para confirmar/desmentir no primeiro log real.
    """
    listings = []
    html = fetch_html("https://artbid.pt/en/lots")
    if not html:
        return listings
    soup = BeautifulSoup(html, "html.parser")
    cards = [a for a in soup.find_all("a", href=True) if PRICE_PATTERN.search(a.get_text(separator=" "))]
    if not cards:
        log.warning(
            "[Artbid] 0 lotes com preço encontrados no HTML inicial — "
            "consistente com a suspeita de que a grelha de lotes só é "
            "gerada por JavaScript (ver diagnóstico 18/08/2026 no código)."
        )
    seen_hrefs = set()
    for card in cards[:20]:
        href = card.get("href", "")
        if not href or href in seen_hrefs:
            continue
        seen_hrefs.add(href)
        title = clean_text(card.get_text(separator=" "))
        url = href if href.startswith("http") else f"https://artbid.pt{href}"
        match = PRICE_PATTERN.search(card.get_text(separator=" "))
        price = parse_price(match.group()) if match else None
        if not title:
            continue
        listings.append(Listing(
            portal="Artbid", category="arte", external_id=url,
            title=title, price=price, market_estimate=price * 1.15 if price else None,
            currency="EUR", url=url,
            details={"fonte_raw": "artbid_http"},
        ))
    log.info(f"[Artbid] {len(listings)} anúncios")
    return listings


def scrape_cabral_moncada() -> list[Listing]:
    """
    Adicionada 18/08/2026 a pedido explícito, apesar de confiança MUITO
    BAIXA: verifiquei a homepage, /leiloes/online e a página de um leilão
    concreto (/leiloes/fa/online/1655) — nenhuma mostra lotes com título e
    valor de licitação no HTML inicial, só navegação/estrutura do site. É
    bem provável que isto dê sempre 0 até resolvermos com browser headless
    ou API. Código incluído mesmo assim, com diagnóstico para confirmar no
    primeiro log real.
    """
    listings = []
    html = fetch_html("https://www.cml.pt/leiloes/online")
    if not html:
        return listings
    soup = BeautifulSoup(html, "html.parser")
    cards = [a for a in soup.find_all("a", href=True) if PRICE_PATTERN.search(a.get_text(separator=" "))]
    if not cards:
        log.warning(
            "[Cabral Moncada Leilões] 0 lotes com preço encontrados no HTML "
            "inicial — consistente com a suspeita de que os lotes só são "
            "gerados por JavaScript (ver diagnóstico 18/08/2026 no código)."
        )
    seen_hrefs = set()
    for card in cards[:20]:
        href = card.get("href", "")
        if not href or href in seen_hrefs:
            continue
        seen_hrefs.add(href)
        title = clean_text(card.get_text(separator=" "))
        url = href if href.startswith("http") else f"https://www.cml.pt{href}"
        match = PRICE_PATTERN.search(card.get_text(separator=" "))
        price = parse_price(match.group()) if match else None
        if not title:
            continue
        listings.append(Listing(
            portal="Cabral Moncada Leilões", category="arte", external_id=url,
            title=title, price=price, market_estimate=price * 1.15 if price else None,
            currency="EUR", url=url,
            details={"fonte_raw": "cabral_moncada_http"},
        ))
    log.info(f"[Cabral Moncada Leilões] {len(listings)} anúncios")
    return listings


def run_all_http_scrapers(zones: list[str], enabled: set[str] | None = None) -> list[tuple[str, list[Listing]]]:
    """
    Corre os scrapers HTTP cujo portal esteja activo. `enabled` vem de
    core.sources_config.load_enabled_sources() — None significa "tudo
    activo" (comportamento antigo, sem filtragem).
    """
    from core.sources_config import is_enabled  # import local: evita import circular no arranque do módulo

    sources = [
        ("Casa Sapo", lambda: scrape_casa_sapo(zones)),
        ("Custo Justo", lambda: scrape_custo_justo(zones)),
        ("Properstar", lambda: scrape_properstar()),
        ("Mitula", lambda: scrape_mitula(zones)),
        ("Mobile.de", lambda: scrape_mobilede()),
        ("AutoUncle", lambda: scrape_autouncle()),
        ("Watchfinder", lambda: scrape_watchfinder()),
        ("JoliCloset", lambda: scrape_jolicloset()),
        ("Standvirtual", lambda: scrape_standvirtual()),
        ("Onebid", lambda: scrape_onebid()),
        ("Artbid", lambda: scrape_artbid()),
        ("Cabral Moncada Leilões", lambda: scrape_cabral_moncada()),
    ]
    results = []
    for portal_name, fn in sources:
        if not is_enabled(portal_name, enabled):
            log.info(f"[{portal_name}] ignorado (desactivado em config/sources.json)")
            results.append((portal_name, None))  # None = ignorado, distingue de "correu e deu 0"
            continue
        results.append((portal_name, fn()))
    return results
