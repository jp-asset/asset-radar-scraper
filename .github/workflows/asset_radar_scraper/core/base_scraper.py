"""Classe base para todos os scrapers — garante interface consistente."""
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
    needs_browser: bool = False

    def __init__(self, http_client: HttpClient, browser: BrowserClient | None = None):
        self.http_client = http_client
        self.browser = browser if self.needs_browser else None

    @abstractmethod
    def build_search_urls(self, zones: list[str]) -> list[str]:
        ...

    @abstractmethod
    def parse_listings(self, html: str, source_url: str) -> list[Listing]:
        ...

    def _save_debug_html(self, html: str, url: str):
        """
        Grava uma amostra do HTML para calibração de seletores.

        IMPORTANTE: `html` chega aqui já como string Python (não bytes),
        decodificada corretamente por safe_decode_response() ou por
        page.content() do Playwright — ambos já tratam o encoding.
        Gravamos sempre com encoding="utf-8" explícito para garantir
        que o ficheiro fica legível e sem corrupção de caracteres.
        """
        if not DEBUG_HTML_DIR:
            return
        try:
            os.makedirs(DEBUG_HTML_DIR, exist_ok=True)
            safe_name = self.portal_name.lower().replace(" ", "_").replace(".", "")
            path = os.path.join(DEBUG_HTML_DIR, f"{safe_name}.html")
            if not os.path.exists(path):
                # Validação extra: confirma que não há excesso de caracteres de substituição
                # (sinal de que o encoding já vinha corrompido antes de chegar aqui)
                replacement_count = html.count("\ufffd")
                if replacement_count > len(html) * 0.05:  # mais de 5% corrompido
                    log.warning(
                        f"[DEBUG] {self.portal_name}: {replacement_count} caracteres de substituição "
                        f"detetados ({replacement_count/max(len(html),1)*100:.1f}%) — possível problema de encoding"
                    )
                with open(path, "w", encoding="utf-8", errors="replace") as f:
                    f.write(f"<!-- URL: {url} -->\n")
                    f.write(html[:500000])
                log.info(f"[DEBUG] HTML de {self.portal_name} gravado em {path} ({len(html)} chars)")
        except Exception as e:
            log.warning(f"[DEBUG] falha ao gravar HTML de {self.portal_name}: {e}")

    def run(self, zones: list[str]) -> list[Listing]:
        all_listings: list[Listing] = []
        urls = self.build_search_urls(zones)
        for url in urls:
            result = fetch_with_fallback(url, self.http_client, self.browser)
            if not result.success:
                log.warning(f"[{self.portal_name}] falhou em {url}: {result.blocked_reason}")
                # Grava mesmo quando falha, para diagnóstico (ex: ver página de bloqueio)
                if result.html:
                    self._save_debug_html(result.html, url)
                continue
            self._save_debug_html(result.html, url)
            try:
                listings = self.parse_listings(result.html, url)
                for l in listings:
                    l.compute_score()
                all_listings.extend(listings)
                log.info(f"[{self.portal_name}] {len(listings)} anúncios extraídos de {url}")
            except Exception as e:
                log.error(f"[{self.portal_name}] erro ao processar {url}: {e}")
        return all_listings
