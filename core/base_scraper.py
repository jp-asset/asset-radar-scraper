"""Classe base para todos os scrapers."""
from abc import ABC, abstractmethod
from core.models import Listing
from core.http_client import HttpClient, BrowserClient, fetch_with_fallback
import logging
import os
 
log = logging.getLogger("asset_radar")
DEBUG_HTML_DIR = os.environ.get("DEBUG_HTML_DIR")
 
 
class BaseScraper(ABC):
    portal_name: str = "base"
    category: str = "geral"
    needs_browser: bool = False  # mantido por compatibilidade, não usado com Scrapfly
    render_js: bool = True       # False = 5 créditos/pedido; True = 25 créditos/pedido
 
    def __init__(self, http_client: HttpClient, browser: BrowserClient | None = None):
        self.http_client = http_client
        self.browser = browser
 
    @abstractmethod
    def build_search_urls(self, zones: list[str]) -> list[str]:
        ...
 
    @abstractmethod
    def parse_listings(self, html: str, source_url: str) -> list[Listing]:
        ...
 
    def _save_debug_html(self, html: str, url: str):
        if not DEBUG_HTML_DIR or not html:
            return
        try:
            os.makedirs(DEBUG_HTML_DIR, exist_ok=True)
            safe_name = self.portal_name.lower().replace(" ", "_").replace(".", "")
            path = os.path.join(DEBUG_HTML_DIR, f"{safe_name}.html")
            if not os.path.exists(path):
                with open(path, "w", encoding="utf-8", errors="replace") as f:
                    f.write(f"<!-- URL: {url} -->\n")
                    f.write(html[:500000])
                log.info(f"[DEBUG] HTML de {self.portal_name} gravado ({len(html)} chars)")
        except Exception as e:
            log.warning(f"[DEBUG] falha ao gravar HTML de {self.portal_name}: {e}")
 
    def run(self, zones: list[str]) -> list[Listing]:
        all_listings: list[Listing] = []
        urls = self.build_search_urls(zones)
        for url in urls:
            result = fetch_with_fallback(
                url, self.http_client, self.browser,
                render_js=self.render_js,
            )
            if not result.success:
                log.warning(f"[{self.portal_name}] falhou em {url}: {result.blocked_reason}")
                if result.html:
                    self._save_debug_html(result.html, url)
                continue
            self._save_debug_html(result.html, url)
            try:
                listings = self.parse_listings(result.html, url)
                for l in listings:
                    l.compute_score()
                all_listings.extend(listings)
                log.info(f"[{self.portal_name}] {len(listings)} anúncios de {url}")
            except Exception as e:
                log.error(f"[{self.portal_name}] erro ao processar {url}: {e}")
        return all_listings
 
