# Asset Radar — Motor de Scraping Diário (Custo Zero)

## O que isto é

Um sistema completo que corre **1x por dia, gratuitamente, no GitHub Actions**, faz scraping real
das 14 fontes configuradas, e grava o resultado num ficheiro JSON que a tua app no Netlify lê
diretamente. Sem servidor pago, sem base de dados paga, sem subscrição de scraping.

## Arquitetura (e porque é grátis)

```
GitHub Actions (1x/dia, grátis)
   │
   ├─ FASE 1: scrapers HTTP simples (rápidos, sem browser)
   │     Mitula, AutoUncle, JoliCloset
   │
   ├─ FASE 2: scrapers com browser Playwright (só os que precisam)
   │     Idealista, Imovirtual, Casa Sapo, Custo Justo, Properstar,
   │     OLX, AutoScout24, Mobile.de, Chrono24, Watchfinder, Catawiki
   │
   ├─ Remove duplicados, calcula scores
   │
   └─ Grava data/opportunities.json → git commit → git push
                                              │
                                              ▼
                            GitHub serve este ficheiro via raw.githubusercontent.com
                                              │
                                              ▼
                              A tua app no Netlify faz fetch() a este URL
```

**Custo: €0/mês.** GitHub Actions é gratuito até 2.000 minutos/mês em repos privados,
e **ilimitado em repos públicos**. Um scan completo demora 5-15 minutos — mesmo
correndo todos os dias, isto fica muito longe do limite.

## Passo 1 — Publicar este código no GitHub

```bash
cd asset_radar_scraper
git init
git add .
git commit -m "Setup inicial do motor de scraping"
gh repo create asset-radar-scraper --public --source=. --push
# ou manualmente: cria o repo em github.com/new e faz git remote add + push
```

**Importante:** usa um repositório **público** para teres minutos de Actions ilimitados.
Se preferires privado, tens 2.000 min/mês grátis — ainda suficiente para 1 scan/dia.

## Passo 2 — Ativar o GitHub Actions

Depois do push, vai à aba "Actions" do teu repositório no GitHub. O workflow
`daily-scan.yml` já está configurado para correr todos os dias às 06:00 UTC,
e também podes correr manualmente clicando "Run workflow".

## Passo 3 — Ligar a app Netlify ao resultado

No ficheiro `index.html` da tua app, procura a linha:

```js
const SCAN_DATA_URL = 'https://raw.githubusercontent.com/SEU_USER/asset-radar-scraper/main/data/opportunities.json';
```

Substitui `SEU_USER` pelo teu utilizador GitHub real. Faz novo deploy da app no Netlify.

## O que vais ver no início

**O scraping real vai falhar nalgumas fontes — isto é esperado e normal.** Os seletores
CSS em cada scraper (`scrapers/*.py`) são uma primeira aproximação, baseada em padrões
comuns destes sites — não foram validados contra o HTML real porque o ambiente onde
este código foi escrito não tem acesso de rede a estes sites para os testar ao vivo.

**Depois do primeiro scan correr no GitHub Actions:**

1. Vai à aba "Actions" → abre a execução → lê o resumo no final dos logs
2. Vais ver algo como:
   ```
   Imovirtual    [browser] 8 anúncios
   Idealista     [browser] erro: seletor não encontrado
   Casa Sapo     [browser] 0 anúncios
   ```
3. Para as fontes com 0 resultados ou erro, é preciso **ajustar os seletores CSS**
   em `scrapers/<fonte>.py` — inspecionando o HTML real dessa página (botão direito →
   Inspecionar no browser, no site real) e corrigindo os `.select_one(...)` para
   corresponder à estrutura atual do site.

Isto é trabalho normal de manutenção de scraping — os sites mudam o HTML com frequência,
e scrapers precisam de ajuste contínuo. Não há forma de evitar esta primeira ronda de calibração.

## Estrutura do projeto

```
asset_radar_scraper/
├── core/
│   ├── http_client.py      — cliente HTTP + browser Playwright com fallback automático
│   ├── models.py           — modelo de dados normalizado (Listing)
│   ├── normalize.py        — parsing de preços/áreas de texto livre
│   ├── config.py           — zonas, preços de referência
│   └── base_scraper.py     — interface comum a todos os scrapers
├── scrapers/
│   ├── imovirtual.py, casasapo.py, idealista.py
│   ├── imobiliario_secundario.py  (Custo Justo, Properstar, Mitula)
│   ├── autoscout24.py, chrono24.py, catawiki.py, jolicloset.py
│   └── diversos.py          (OLX, Watchfinder, Mobile.de, AutoUncle)
├── run_scan.py              — orquestrador principal
├── requirements.txt
└── .github/workflows/daily-scan.yml
```

## Otimizações de custo já aplicadas

1. **Browser só liga uma vez por scan**, reutilizado entre todas as fontes que precisam
   de JS — em vez de abrir/fechar Chromium por fonte (isso seria 10-15x mais lento).
2. **HTTP simples tentado primeiro em todas as fontes** — só sobe para browser nas que
   especificamente têm `needs_browser = True`, confirmado no diagnóstico anterior.
3. **GitHub Actions com repo público** — minutos ilimitados, zero custo mesmo a longo prazo.
4. **Dados em JSON no git**, sem base de dados paga — o histórico de scans fica gravado
   automaticamente no histórico de commits, sem custo extra.

## Manutenção esperada

Scraping real exige manutenção contínua: quando um site muda o design, o scraper
correspondente para de funcionar até os seletores serem corrigidos. Isto é normal e
esperado — não é um bug do código, é a natureza de depender de HTML não-controlado.
Recomenda-se rever os logs do GitHub Actions semanalmente.
