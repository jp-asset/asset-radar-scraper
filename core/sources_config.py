"""
Controlo de que fontes correm em cada scan — para poupar créditos Apify
(fontes 'apify_actor') e tempo (fontes 'http_directo') sem apagar código.

Prioridade de configuração (a primeira que existir vence):
  1. Variável de ambiente SOURCES_OVERRIDE — lista de nomes de portal
     separados por vírgulas (ex: "Imovirtual,Catawiki"), ou a palavra
     "all" para activar tudo. Pensada para runs manuais pontuais — ver o
     input "sources" em Actions -> Run workflow — sem tocar no ficheiro de
     configuração persistente.
  2. config/sources.json — configuração persistente, editável directamente
     no GitHub (ícone de lápis -> editar -> commit). É o que o cron diário
     automático usa, porque não pode receber inputs manuais.
  3. Se nenhuma das duas existir ou for legível, todas as fontes ficam
     activas por omissão — nunca falha silenciosamente para "0 fontes".

Chaves no JSON que começam por "_" são comentários e são ignoradas (JSON
não suporta comentários nativos).
"""
import json
import logging
import os

log = logging.getLogger("asset_radar")

CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "config", "sources.json",
)


def load_enabled_sources() -> set[str] | None:
    """Devolve o set de nomes de portal activos, ou None = sem restrição (tudo activo)."""
    override = os.environ.get("SOURCES_OVERRIDE", "").strip()
    if override:
        if override.lower() == "all":
            log.info("[Config] SOURCES_OVERRIDE=all — todas as fontes activas (override manual).")
            return None
        names = {n.strip() for n in override.split(",") if n.strip()}
        log.info(f"[Config] SOURCES_OVERRIDE activo — só vão correr: {sorted(names)}")
        return names

    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        log.info("[Config] config/sources.json não encontrado — todas as fontes activas por omissão.")
        return None
    except (json.JSONDecodeError, OSError) as e:
        log.warning(
            f"[Config] Erro a ler config/sources.json ({e}) — todas as "
            "fontes activas por omissão, para o scan não parar por causa disto."
        )
        return None

    portals = {k: v for k, v in data.items() if not k.startswith("_")}
    enabled = {name for name, on in portals.items() if on}
    disabled = sorted(name for name, on in portals.items() if not on)
    if disabled:
        log.info(f"[Config] Fontes desactivadas em config/sources.json: {disabled}")
    return enabled


def is_enabled(portal_name: str, enabled: set[str] | None) -> bool:
    return enabled is None or portal_name in enabled
