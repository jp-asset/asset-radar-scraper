"""
Core HTTP client para o Asset Radar Scraper Engine.
 
Usa o Scrapfly como camada de transporte — resolve automaticamente:
- Proxies residenciais rotativos (IPs limpos, não de datacenter)
- Anti-bot bypass (DataDome, Cloudflare, Akamai)
- JavaScript rendering quando necessário
- TLS fingerprinting correto
 
A API key é lida da variável de ambiente SCRAPFLY_API_KEY.
"""
import time
import logging
import os
from dataclasses import dataclass
from typing import Optional
 
log = logging.getLogger("asset_radar")
 
CHALLENGE_SIGNALS = [
    "datadome", "cf-challenge", "cloudflare", "are you human",
    "captcha", "unusual traffic", "access denied",
    "verifying you are human", "checking your browser", "just a moment",
]
 
 
@dataclass
class FetchResult:
    url: str
    status: int
    html: str = ""
    method: str = "scrapfly"
    success: bool = False
    blocked_reason: Optional[str] = None
    elapsed_ms: int = 0
 
 
class ScrapflyClient:
    """
    Cliente Scrapfly — substitui HttpClient + BrowserClient.
    Um único cliente lida com todos os sites, com ou sem JS rendering.
    """
 
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("SCRAPFLY_API_KEY", "")
        if not self.api_key:
            raise ValueError("SCRAPFLY_API_KEY não definida. Configura nas variáveis de ambiente do GitHub Actions.")
        from scrapfly import ScrapflyClient as _Client
        self._client = _Client(key=self.api_key)
 
    def fetch(self, url: str, render_js: bool = True, country: str = "PT") -> FetchResult:
        start = time.time()
        try:
            from scrapfly import ScrapeConfig
            result = self._client.scrape(ScrapeConfig(
                url=url,
                asp=True,           # Anti-Scraping Protection bypass
                render_js=render_js,
                country=country,
                retry=False,
            ))
            elapsed = int((time.time() - start) * 1000)
            html = result.scrape_result.get("content", "")
            status = result.result.get("status_code", 0)
            html_lower = html.lower()
            has_challenge = any(sig in html_lower for sig in CHALLENGE_SIGNALS)
 
            if has_challenge:
                log.warning(f"[Scrapfly] challenge detetado em {url}")
                return FetchResult(url, status, html, "scrapfly", False, "challenge", elapsed)
            if status in (403, 429):
                return FetchResult(url, status, html, "scrapfly", False, f"http_{status}", elapsed)
            if len(html) < 500:
                return FetchResult(url, status, html, "scrapfly", False, "resposta_curta", elapsed)
 
            log.info(f"✓ Scrapfly {url} — {status}, {len(html)} bytes, {elapsed}ms")
            return FetchResult(url, status, html, "scrapfly", True, None, elapsed)
 
        except Exception as e:
            elapsed = int((time.time() - start) * 1000)
            log.error(f"[Scrapfly] erro em {url}: {e}")
            return FetchResult(url, 0, "", "scrapfly", False, f"erro:{e}", elapsed)
 
    def close(self):
        try:
            self._client.close()
        except Exception:
            pass
 
 
# Alias para compatibilidade com base_scraper.py
HttpClient = ScrapflyClient
 
 
class BrowserClient:
    """
    Stub de compatibilidade — com Scrapfly não precisamos de browser separado.
    O ScrapflyClient já lida com JS rendering internamente.
    """
    def __init__(self, headless=True):
        pass
 
    def __enter__(self):
        return self
 
    def __exit__(self, *args):
        pass
 
 
def fetch_with_fallback(
    url: str,
    http_client,
    browser=None,
    wait_selector: Optional[str] = None,
) -> FetchResult:
    """
    Com Scrapfly, um único pedido resolve tudo.
    O parâmetro `browser` é ignorado — mantido para compatibilidade.
    """
    return http_client.fetch(url, render_js=True)
