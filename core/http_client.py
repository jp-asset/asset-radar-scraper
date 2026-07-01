"""
Core HTTP client para o Asset Radar Scraper Engine.
Usa Scrapfly como camada de transporte.
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
 
 
def safe_decode_response(html: str) -> str:
    """Valida que o HTML não está corrompido (mais de 5% de caracteres de substituição)."""
    if not html:
        return html
    replacement_count = html.count("\ufffd")
    if replacement_count > len(html) * 0.05:
        log.warning(f"HTML possivelmente corrompido: {replacement_count} chars de substituição")
    return html
 
 
class ScrapflyClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("SCRAPFLY_API_KEY", "")
        if not self.api_key:
            raise ValueError("SCRAPFLY_API_KEY não definida.")
        from scrapfly import ScrapflyClient as _Client
        self._client = _Client(key=self.api_key)
 
    def fetch(self, url: str, render_js: bool = True, country: str = "PT") -> FetchResult:
        start = time.time()
        try:
            from scrapfly import ScrapeConfig
            result = self._client.scrape(ScrapeConfig(
                url=url,
                asp=True,
                render_js=render_js,
                country=country,
                retry=False,
            ))
            elapsed = int((time.time() - start) * 1000)
            html = result.scrape_result.get("content", "")
            html = safe_decode_response(html)
            status = result.result.get("status_code", 0)
            html_lower = html.lower()
            has_challenge = any(sig in html_lower for sig in CHALLENGE_SIGNALS)
 
            if has_challenge:
                log.warning(f"[Scrapfly] challenge em {url}")
                return FetchResult(url, status, html, "scrapfly", False, "challenge", elapsed)
            if status in (403, 429):
                return FetchResult(url, status, html, "scrapfly", False, f"http_{status}", elapsed)
            if len(html) < 500:
                log.warning(f"[Scrapfly] resposta curta ({len(html)} bytes) em {url}")
                return FetchResult(url, status, html, "scrapfly", False, "resposta_curta", elapsed)
 
            log.info(f"✓ Scrapfly {url} — {status}, {len(html)} bytes, {elapsed}ms, render_js={render_js}")
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
 
 
# Alias para compatibilidade
HttpClient = ScrapflyClient
 
 
class BrowserClient:
    """Stub de compatibilidade — Scrapfly substitui o browser."""
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
    render_js: bool = True,
) -> FetchResult:
    """Com Scrapfly, um único pedido resolve tudo. render_js controla o custo em créditos."""
    return http_client.fetch(url, render_js=render_js)
 
