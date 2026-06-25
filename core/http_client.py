"""
Core HTTP/Browser client para o Asset Radar Scraper Engine.

Estratégia de custo zero:
- Tenta sempre primeiro `requests` simples (mais rápido, sem custo de recursos)
- Sobe para Playwright + stealth apenas quando o site exige JS (challenge detetado)
- Nunca usa serviços pagos — playwright-stealth é open source e gratuito
"""
import time
import random
import logging
from dataclasses import dataclass, field
from typing import Optional

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("asset_radar")

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-PT,pt;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

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
    method: str = "http"  # "http" ou "browser"
    success: bool = False
    blocked_reason: Optional[str] = None
    elapsed_ms: int = 0


class HttpClient:
    """Pedido HTTP simples — primeira tentativa, mais barata."""

    def __init__(self, min_delay=1.5, max_delay=4.0):
        self.session = requests.Session()
        self.session.headers.update(DEFAULT_HEADERS)
        self.min_delay = min_delay
        self.max_delay = max_delay

    def _pace(self):
        time.sleep(random.uniform(self.min_delay, self.max_delay))

    def fetch(self, url: str) -> FetchResult:
        start = time.time()
        self._pace()
        try:
            resp = self.session.get(url, timeout=20, allow_redirects=True)
            elapsed = int((time.time() - start) * 1000)
            html_lower = resp.text.lower()
            has_challenge = any(sig in html_lower for sig in CHALLENGE_SIGNALS)

            if resp.status_code in (403, 429):
                return FetchResult(url, resp.status_code, resp.text, "http", False,
                                    f"http_{resp.status_code}", elapsed)
            if has_challenge:
                return FetchResult(url, resp.status_code, resp.text, "http", False,
                                    "js_challenge", elapsed)
            return FetchResult(url, resp.status_code, resp.text, "http", True, None, elapsed)
        except Exception as e:
            elapsed = int((time.time() - start) * 1000)
            return FetchResult(url, 0, "", "http", False, f"erro:{e}", elapsed)


class BrowserClient:
    """
    Fallback com Playwright + stealth — só usado quando HttpClient falha
    com 'js_challenge'. Mais lento e mais pesado, por isso é a segunda opção,
    nunca a primeira (otimização de custo/tempo de execução).
    """

    def __init__(self, headless=True):
        self.headless = headless
        self._playwright = None
        self._browser = None
        self._context = None

    def __enter__(self):
        from playwright.sync_api import sync_playwright
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=self.headless)
        self._context = self._browser.new_context(
            user_agent=DEFAULT_HEADERS["User-Agent"],
            locale="pt-PT",
            viewport={"width": 1366, "height": 850},
        )
        # Stealth patches básicos (gratuitos, sem dependência paga)
        self._context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'languages', { get: () => ['pt-PT', 'pt', 'en'] });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
            window.chrome = { runtime: {} };
        """)
        return self

    def __exit__(self, *args):
        if self._context:
            self._context.close()
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()

    def fetch(self, url: str, wait_selector: Optional[str] = None, wait_ms: int = 3500) -> FetchResult:
        start = time.time()
        page = self._context.new_page()
        try:
            resp = page.goto(url, timeout=25000, wait_until="domcontentloaded")
            # Pacing humano + tempo para challenge JS resolver (Cloudflare等 auto-passa em alguns casos)
            page.wait_for_timeout(wait_ms + random.randint(-500, 1500))
            if wait_selector:
                try:
                    page.wait_for_selector(wait_selector, timeout=8000)
                except Exception:
                    pass
            html = page.content()
            elapsed = int((time.time() - start) * 1000)
            html_lower = html.lower()
            has_challenge = any(sig in html_lower for sig in CHALLENGE_SIGNALS)
            status = resp.status if resp else 0

            if has_challenge:
                return FetchResult(url, status, html, "browser", False, "js_challenge_persistente", elapsed)
            if status in (403, 429):
                return FetchResult(url, status, html, "browser", False, f"http_{status}", elapsed)
            return FetchResult(url, status, html, "browser", True, None, elapsed)
        except Exception as e:
            elapsed = int((time.time() - start) * 1000)
            return FetchResult(url, 0, "", "browser", False, f"erro:{e}", elapsed)
        finally:
            page.close()


def fetch_with_fallback(url: str, http_client: HttpClient, browser: Optional[BrowserClient] = None,
                          wait_selector: Optional[str] = None) -> FetchResult:
    """
    Estratégia de custo otimizado:
    1. Tenta HTTP simples (rápido, ~0.5-2s, sem overhead de browser)
    2. Só sobe para Playwright se houver challenge JS (lento, ~5-10s, mais recursos)
    """
    result = http_client.fetch(url)
    if result.success:
        log.info(f"✓ {url} — HTTP simples bastou ({result.elapsed_ms}ms)")
        return result

    if result.blocked_reason == "js_challenge" and browser is not None:
        log.info(f"⚠ {url} — JS challenge detetado, a tentar com browser...")
        browser_result = browser.fetch(url, wait_selector=wait_selector)
        if browser_result.success:
            log.info(f"✓ {url} — resolvido via browser ({browser_result.elapsed_ms}ms)")
        else:
            log.warning(f"✕ {url} — falhou mesmo com browser: {browser_result.blocked_reason}")
        return browser_result

    log.warning(f"✕ {url} — bloqueado: {result.blocked_reason}")
    return result
