"""Classe base para todos os scrapers — garante interface consistente."""
from abc import ABC, abstractmethod
from core.models import Listing
from core.http_client import HttpClient, BrowserClient, fetch_with_fallback
import logging

log = logging.getLogger("asset_radar")


class BaseScraper(ABC):
    portal_name: str = "base"
    category: str = "geral"
    needs_browser: bool = False  # True para fontes com JS challenge confirmado no diagnóstico

    def __init__(self, http_client: HttpClient, browser: BrowserClient | None = None):
        self.http_client = http_client
        self.browser = browser if self.needs_browser else None

    @abstractmethod
    def build_search_urls(self, zones: list[str]) -> list[str]:
        """Devolve a lista de URLs a pesquisar para este portal."""
        ...

    @abstractmethod
    def parse_listings(self, html: str, source_url: str) -> list[Listing]:
        """Extrai anúncios do HTML devolvido."""
        ...

    def run(self, zones: list[str]) -> list[Listing]:
        all_listings: list[Listing] = []
        urls = self.build_search_urls(zones)
        for url in urls:
            result = fetch_with_fallback(url, self.http_client, self.browser)
            if not result.success:
                log.warning(f"[{self.portal_name}] falhou em {url}: {result.blocked_reason}")
                continue
            try:
                listings = self.parse_listings(result.html, url)
                for l in listings:
                    l.compute_score()
                all_listings.extend(listings)
                log.info(f"[{self.portal_name}] {len(listings)} anúncios extraídos de {url}")
            except Exception as e:
                log.error(f"[{self.portal_name}] erro ao processar {url}: {e}")
        return all_listings
