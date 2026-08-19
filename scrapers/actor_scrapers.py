"""
Scrapers que usam actors prontos do Apify marketplace.
Zero manutencao de seletores — os autores dos actors mantem-nos actualizados.

NOTA: run_actor() usa client.run(run.id).dataset() — compativel com apify-client 3.x
"""
import logging
import time
from datetime import timedelta
from core.apify_client import get_apify_client, MAX_RESULTS_PER_SOURCE
from core.models import Listing
from core.normalize import parse_price, parse_area, clean_text
from core.config import ZONE_PRICES_DEFAULT

log = logging.getLogger("asset_radar")


def run_actor(actor_id: str, run_input: dict, timeout_secs: int = 180) -> list[dict]:
    """
    Corre um actor do Apify e devolve os resultados como lista de dicts.
    Usa client.run(run.id).dataset() — forma correcta no apify-client 3.x.
    O objeto devolvido por actor.call() e um Run, nao um dict.
    """
    client = get_apify_client()
    log.info(f"[Apify] A correr actor {actor_id} (max {MAX_RESULTS_PER_SOURCE} resultados)")
    start = time.time()
    try:
        run = client.actor(actor_id).call(
            run_input=run_input,
            memory_mbytes=256,
            wait_duration=timedelta(seconds=timeout_secs),
        )
        if run is None:
            log.warning(f"[Apify] {actor_id}: run devolveu None (timeout?)")
            return []
        elapsed = round(time.time() - start, 1)
        items = list(client.run(run.id).dataset().iterate_items())
        log.info(f"[Apify] {actor_id}: {len(items)} resultados em {elapsed}s")
        return items
    except Exception as e:
        elapsed = round(time.time() - start, 1)
        log.error(f"[Apify] {actor_id} falhou apos {elapsed}s: {e}")
        return []


class ImovirtualActorScraper:
    """
    Actor: solidcode/imovirtual-scraper

    CALIBRADO 17/08/2026 — dois bugs no input confirmados contra o input schema
    publicado (apify.com/solidcode/imovirtual-scraper/input-schema):
      1. `location` tem de ser o nome da cidade/região em português com
         acentos (ex: "Lisboa"), não um slug em minúsculas ("lisboa") — o
         actor não faz essa normalização.
      2. `propertyType` é enum fechado: any/apartment/house/land/commercial/
         garage/room/warehouse/development. "apartamento" não é um valor
         válido, pelo que era provavelmente ignorado ou rejeitado — devolvia
         0 resultados. Corrigido para "apartment".
    """
    portal_name = "Imovirtual"
    category = "imovel"
    actor_id = "solidcode/imovirtual-scraper"

    def run(self, zones: list[str]) -> list[Listing]:
        listings = []
        for zone in zones[:2]:
            location = {"Lisboa Centro": "Lisboa", "Porto Centro": "Porto",
                        "Cascais": "Cascais"}.get(zone, "Lisboa")
            items = run_actor(self.actor_id, {
                "location": location,
                "transaction": "buy",
                "propertyType": "apartment",
                "maxResults": MAX_RESULTS_PER_SOURCE,
            })
            for item in items:
                price = parse_price(item.get("price") or item.get("totalPrice"))
                area = parse_area(item.get("area") or item.get("livingArea"))
                url = item.get("url", "")
                title = clean_text(item.get("title") or f"Apartamento {zone}")
                if not url:
                    continue
                ppm2 = ZONE_PRICES_DEFAULT.get(zone, 5000)
                market = ppm2 * area if area else None
                listings.append(Listing(
                    portal=self.portal_name, category=self.category,
                    external_id=url, title=title, price=price,
                    market_estimate=market, currency="EUR", url=url,
                    zone=zone, area_m2=area,
                    posted_date=item.get("dateCreated"),
                    details={
                        "tipologia": item.get("rooms", ""),
                        "casas_banho": item.get("bathrooms", ""),
                        "fonte_raw": "imovirtual_actor",
                    },
                ))
        return listings


class IdealistaActorScraper:
    """
    Actor: lukass/idealista-scraper

    CALIBRADO 17/08/2026 — três problemas identificados contra a documentação
    pública do actor:
      1. Nomes de campo errados: o schema usa `startUrl` (singular) e
         `maxItems`, não `startUrls`/`maxResults` — os valores enviados
         eram provavelmente ignorados por não corresponderem a nenhum campo.
      2. `propertyType: "homes"` não existe no schema deste actor (schema
         tem `homeType`, não `propertyType`) — removido.
      3. A documentação do actor indica explicitamente "RESIDENTIAL proxies
         required" e não estávamos a enviar nenhuma config de proxy — isto é
         a explicação mais provável para os timeouts (o actor fica bloqueado
         pelo anti-bot da Idealista sem proxy residencial e nunca devolve
         dados dentro do tempo limite).

    CORRIGIDO 18/08/2026 — causa raíz confirmada no log real do run #74: o
    actor tenta resolver a localização "lisboa" via uma API interna de
    geocoding da Idealista (`/api/3/pt/locations?prefix=lisboa...`) *antes*
    de sequer chegar ao `startUrl`, e esse pedido levava sempre HTTP 406
    (bloqueio anti-bot), mesmo depois de "8 retries". O motivo: o nome do
    campo de proxy estava errado. O schema publicado do actor tem um campo
    próprio chamado `proxy` (Object, obrigatório) — não `proxyConfiguration`
    (essa é a convenção genérica do Apify SDK, mas não é o nome que este
    actor em particular usa). Como enviávamos um campo que o actor não
    reconhece, ele corria sem proxy nenhum e a Idealista bloqueava o pedido
    de geocoding imediatamente. Campo corrigido para `proxy`.

    ⚠️ NÃO RESOLVIDO (2ª iteração) 18/08/2026 — confirmei o campo `proxy`
    contra DOIS exemplos reais e independentes da documentação do mesmo
    autor (lukass) — formato `{"useApifyProxy": true, "apifyProxyGroups":
    ["RESIDENTIAL"]}` — e é exactamente o que já estávamos a enviar. Ainda
    assim, o run seguinte falhou de forma IDÊNTICA: mesmo endpoint, mesmo
    HTTP 406, mesmos 8 retries, ao segundo. Ou seja, o nome/formato do campo
    já não é a causa — não há mais nada de plausível a corrigir no lado do
    nosso código. A hipótese mais provável agora é que o pool de proxies
    RESIDENTIAL partilhado do Apify já esteja bloqueado pelo anti-bot da
    Idealista para este endpoint específico (é um alvo popular; blacklistar
    ranges de proxy conhecidos é uma defesa comum) — isto não se resolve por
    tentativa e erro no input. Recomendação: não insistir mais nesta via;
    seguir com o pedido de acesso à API oficial da Idealista já preparado.
    """
    portal_name = "Idealista"
    category = "imovel"
    actor_id = "lukass/idealista-scraper"

    def run(self, zones: list[str]) -> list[Listing]:
        items = run_actor(self.actor_id, {
            "country": "pt",
            "operation": "sale",
            "startUrl": [{"url": "https://www.idealista.pt/comprar-casas/lisboa/"}],
            "maxItems": MAX_RESULTS_PER_SOURCE,
            "proxy": {"useApifyProxy": True, "apifyProxyGroups": ["RESIDENTIAL"]},
        }, timeout_secs=240)
        listings = []
        for item in items:
            price = parse_price(item.get("price"))
            area = parse_area(item.get("size"))
            url = item.get("url", "")
            title = clean_text(item.get("title") or item.get("description", "")[:60])
            if not url:
                continue
            zone = item.get("district") or item.get("neighborhood") or "Lisboa"
            ppm2 = ZONE_PRICES_DEFAULT.get(zone, 5000)
            market = ppm2 * area if area else None
            listings.append(Listing(
                portal=self.portal_name, category=self.category,
                external_id=url, title=title, price=price,
                market_estimate=market, currency="EUR", url=url,
                zone=zone, area_m2=area,
                details={"fonte_raw": "idealista_actor"},
            ))
        return listings


class OLXActorScraper:
    """
    Actor: piotrv1001/olx-listings-scraper

    CORRIGIDO 18/08/2026 — causa raíz confirmada no log real do run #74: o
    campo `mode` deste actor tem valor por defeito "search" (não "urls"), e
    quando `mode` não é explicitado, o `startUrls` que enviávamos era
    completamente ignorado — o actor caía no modo de pesquisa por texto e
    usava o `searchQuery` por defeito, que é literalmente "iphone". Prova
    directa no log: o pedido real feito foi
    `.../api/v1/offers/?...&query=iphone`, e depois desse pedido falhar
    (schema validation da própria Apify ao gravar os itens — bug conhecido
    deste actor em modo pesquisa livre), o resultado final foi sempre 0.
    Corrigido: `mode` definido explicitamente como "urls" para forçar o uso
    do `startUrls` que já estávamos a enviar.

    CORRIGIDO (2ª iteração) 18/08/2026 — o run seguinte confirmou `mode` como
    a causa certa (deixou de aparecer "query=iphone"), mas a mudança de
    `startUrls` para strings simples estava errada: este actor devolveu
    imediatamente `Input is not valid: Items in input.startUrls at
    positions [0] do not contain valid URLs`. Ao contrário do Chrono24, ESTE
    actor exige mesmo o formato `[{"url": "..."}]` — é o formato original,
    antes de eu o ter mudado por analogia sem confirmar. Revertido.

    CORRIGIDO (3ª iteração) 18/08/2026 — a 2ª iteração também estava errada,
    de forma diferente: com `mode: "urls"` + formato de objecto correcto, o
    actor respondeu `Skipping unsupported URL format:
    https://www.olx.pt/imoveis/` e saiu sem processar nada. Ou seja, o modo
    "urls" deste actor não aceita páginas de categoria/listagem (como
    "/imoveis/") — só páginas de anúncio individual, o que não nos serve
    (não temos uma lista de anúncios individuais à partida).
    Mudança de abordagem: voltar ao `mode: "search"` (o modo por defeito, já
    provado capaz de ir buscar dados reais — foi o que devolveu 52
    resultados com a keyword de teste "iphone" na 1ª iteração, antes de eu
    ainda não ter percebido o que se passava), mas agora com uma keyword
    relevante ("apartamento") em vez de deixar o default do actor.
    ⚠️ RISCO CONHECIDO: nessa 1ª iteração, depois de obter 52 resultados
    para "iphone", o push para o dataset falhou com "Schema validation
    failed" — um erro do lado do próprio actor a validar o que ele mesmo
    tentou gravar, não um erro do nosso input. Não há garantia de que uma
    keyword diferente não sofra do mesmo bug; se isto continuar a dar 0,
    é um problema deste actor específico com o modo de pesquisa livre, não
    algo que se resolva ajustando o nosso lado.
    """
    portal_name = "OLX"
    category = "geral"
    actor_id = "piotrv1001/olx-listings-scraper"

    def run(self, zones: list[str]) -> list[Listing]:
        items = run_actor(self.actor_id, {
            "mode": "search",
            "searchQuery": "apartamento",
            "maxItems": MAX_RESULTS_PER_SOURCE,
            "country": "pt",
        })
        listings = []
        for item in items:
            price = parse_price(item.get("price"))
            url = item.get("url", "")
            title = clean_text(item.get("title", ""))
            if not url or not title:
                continue
            listings.append(Listing(
                portal=self.portal_name, category="imovel",
                external_id=url, title=title, price=price,
                market_estimate=price * 1.15 if price else None,
                currency="EUR", url=url,
                posted_date=item.get("createdAt"),
                details={"fonte_raw": "olx_actor"},
            ))
        return listings


class AutoScout24ActorScraper:
    """
    Actor: fayoussef/autoscout24 (TROCADO 18/08/2026, substitui
    blackfalcondata/autoscout24-scraper)

    HISTÓRICO — blackfalcondata/autoscout24-scraper: nome do campo corrigido
    (`searchUrls`), nome do campo de proxy confirmado (`proxyConfiguration`),
    URL simplificada — mesmo assim falhou de forma idêntica ("fetch failed")
    em 3 runs seguidos, com proxy residencial activo a rodar por 4 IPs
    diferentes. Falha idêntica independente do IP aponta para um bloqueio ao
    nível do próprio actor (fingerprint), não corrigível via input — por
    isso trocámos de actor em vez de continuar a tentar calibrar o mesmo.

    NOVO ACTOR — schema completamente diferente, confirmado contra exemplo
    real da documentação: campos em snake_case (`start_urls`, não
    `searchUrls`), proxy é uma string `proxy_url` (endpoint próprio,
    opcional — "residential proxies used by default" quando vazio, por isso
    omitimos o campo). Campos de saída também diferentes: `listing_url` (não
    `url`), `price`, `make`/`model`/`model_version` (não há um único campo
    de título — construído a partir destes três), `mileage_km`,
    `first_registration`.

    ⚠️ POR CONFIRMAR: a documentação deste actor lista suporte oficial a
    .de/.at/.fr/.it/.es/.nl/.be/.lu/.com — Portugal (.pt) não está entre eles
    (mesma limitação do actor anterior). A própria documentação sugere que
    "URLs de pesquisa directas" podem funcionar para países não listados,
    por isso mantemos a URL .pt directa — mas não há garantia de que este
    actor sequer tente processar esse domínio. Se continuar a 0, o mais
    provável é que nenhum actor deste marketplace suporte o AutoScout24.pt
    de forma fiável — nesse caso a alternativa seria voltar ao HTTP directo
    (scrapers/cheerio_scrapers.py) só para esta fonte.
    """
    portal_name = "AutoScout24"
    category = "carro"
    actor_id = "fayoussef/autoscout24"

    def run(self, zones: list[str]) -> list[Listing]:
        items = run_actor(self.actor_id, {
            "start_urls": [{"url": "https://www.autoscout24.pt/lst?sort=price&desc=0"}],
        }, timeout_secs=240)
        listings = []
        for item in items:
            price = parse_price(item.get("price"))
            url = item.get("listing_url", "")
            make = item.get("make", "")
            model = item.get("model", "")
            version = item.get("model_version", "")
            title = clean_text(" ".join(p for p in [make, model, version] if p))
            if not url or not title:
                continue
            listings.append(Listing(
                portal=self.portal_name, category=self.category,
                external_id=url, title=title, price=price,
                market_estimate=price * 1.15 if price else None,
                currency="EUR", url=url,
                details={
                    "km": str(item.get("mileage_km", "")),
                    "ano": str(item.get("first_registration", "")),
                    "fonte_raw": "autoscout24_actor_v2",
                },
            ))
        return listings


class Chrono24ActorScraper:
    """
    Actor: memo23/chrono24-scraper — usa .com nao .pt

    CALIBRADO 17/08/2026 — o domínio `.com` e os nomes de campo (`startUrls`,
    `maxItems`) já estavam correctos contra a documentação do actor; a nota
    "URL .com não .pt" no registo do projecto estava desactualizada. O risco
    real identificado: por defeito este actor faz `fetchListingDetails=true`
    com `maxIndexPages=10`, um crawl bem mais pesado do que o nosso
    orçamento de 180s/256MB suporta — provável causa do que aparecia como
    "falha de calibração". Limitado explicitamente ao necessário para caber
    no orçamento actual (ver run_actor: timeout_secs=180, memory 256MB).

    CORRIGIDO 18/08/2026 — causa raíz confirmada no log real do run #74: o
    actor recebeu o nosso `startUrls` correctamente (visível no dump do
    input), mas a seguir imprimiu `[START_URLS] []` e
    "No valid start URLs provided" — ou seja, filtrou a nossa entrada como
    inválida. O formato que enviávamos era `[{"url": "..."}]` (convenção
    genérica do Apify SDK para listas de pedidos), mas os exemplos
    documentados deste actor mostram `startUrls` como um array de strings
    simples (ex: `["https://www.chrono24.com/omega/index.htm"]`), sem
    objecto `{"url": ...}` à volta. Corrigido para strings simples.

    CORRIGIDO (2ª iteração) 18/08/2026 — a mudança acima resolveu o input:
    o run seguinte confirmou 50 itens devolvidos pelo actor
    (`itemsPushed=50`) e o nosso run_actor() a lê-los correctamente. O bug
    real estava aqui, no parsing: assumíamos campos `url`/`title`/`brand`/
    `reference`/`year`, nenhum dos quais existe no modo "card" (o modo que
    usamos, com fetchListingDetails=False, mais barato). Os 50 itens eram
    lidos e depois todos descartados por `if not url`. Nome real do campo de
    URL confirmado contra a documentação do actor: `listingUrl` (com
    `sourceUrl` como alternativa). `brand`/`model`/`referenceNumber` só
    existem no modo "detail" (fetchListingDetails=True), que não usamos por
    orçamento — por isso deixaram de ser pedidos aqui. `currency` também
    passa a vir do próprio item em vez de assumir sempre EUR — os vendedores
    do Chrono24 anunciam em várias moedas (USD, GBP, CHF, etc.).
    """
    portal_name = "Chrono24"
    category = "relogio"
    actor_id = "memo23/chrono24-scraper"

    def run(self, zones: list[str]) -> list[Listing]:
        items = run_actor(self.actor_id, {
            "startUrls": ["https://www.chrono24.com/rolex/index.htm"],
            "maxItems": MAX_RESULTS_PER_SOURCE,
            "fetchListingDetails": False,
            "maxIndexPages": 1,
        })
        listings = []
        for item in items:
            price = parse_price(item.get("price"))
            url = item.get("listingUrl") or item.get("sourceUrl") or ""
            title = clean_text(item.get("title") or item.get("subtitle", ""))
            if not url:
                continue
            listings.append(Listing(
                portal=self.portal_name, category=self.category,
                external_id=url, title=title, price=price,
                market_estimate=price * 1.15 if price else None,
                currency=item.get("currency") or "EUR", url=url,
                details={
                    "subtitulo": clean_text(item.get("subtitle", "")),
                    "vendedor": item.get("sellerType", ""),
                    "fonte_raw": "chrono24_actor",
                },
            ))
        return listings


class CatawikiActorScraper:
    """
    Actor: solidcode/catawiki-scraper — usa keywords nao startUrls

    CORRIGIDO 17/08/2026 — BUG CRÍTICO: `currentBid` neste actor não é um
    número, é um objecto com as 3 moedas: {"EUR": 6200, "USD": 6700, "GBP": 5300}.
    O código anterior fazia parse_price(item.get("currentBid") or ...), que
    convertia o dicionário inteiro para texto (str({...})) e extraía todos os
    dígitos encontrados — juntando os 3 valores de moeda num único número
    gigante sem sentido (ex: 6200+6700+5300 concatenados = "620067005300").
    Confirmado nos 96 registos reais do scan de hoje: preços na ordem dos
    600 mil milhões de euros para relógios Rolex. Corrigido para ler
    especificamente currentBid['EUR'], com fallback para currentBidValue
    quando a moeda já vem em EUR.
    """
    portal_name = "Catawiki"
    category = "arte"
    actor_id = "solidcode/catawiki-scraper"

    def run(self, zones: list[str]) -> list[Listing]:
        items = run_actor(self.actor_id, {
            "keywords": ["art", "painting", "sculpture"],
            "maxItems": MAX_RESULTS_PER_SOURCE,
        }, timeout_secs=240)
        listings = []
        for item in items:
            bid = item.get("currentBid")
            if isinstance(bid, dict):
                raw_price = bid.get("EUR")
            elif item.get("currentBidCurrency") == "EUR":
                raw_price = item.get("currentBidValue")
            else:
                raw_price = item.get("price")  # último recurso, pode não existir
            price = parse_price(raw_price)
            url = item.get("url", "")
            title = clean_text(item.get("title", ""))
            if not url or not title:
                continue
            listings.append(Listing(
                portal=self.portal_name, category=self.category,
                external_id=url, title=title, price=price,
                # NOTA: *1.15 é uma estimativa genérica de mercado (não há
                # preço de referência real para arte/leilões, ao contrário do
                # imobiliário que usa €/m² por zona) — por isso dá sempre
                # ~13% de "desconto", o que NÃO é uma comparação de mercado
                # real. Confiança reduzida para reflectir isso.
                market_estimate=price * 1.15 if price else None,
                currency="EUR", url=url,
                confidence=0.45,
                details={"tipo": "leilao", "fonte_raw": "catawiki_actor",
                         "nota_mercado": "estimativa genérica — sem preço de referência real de leilões"},
            ))
        return listings


ALL_ACTOR_SCRAPERS = [
    ImovirtualActorScraper,
    IdealistaActorScraper,
    OLXActorScraper,
    AutoScout24ActorScraper,
    Chrono24ActorScraper,
    CatawikiActorScraper,
]
