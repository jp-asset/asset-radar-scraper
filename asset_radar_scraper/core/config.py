"""Configuração partilhada: zonas, preços de referência."""

ZONE_PRICES_DEFAULT = {
    "Lisboa Centro": 7200, "Parque das Nações": 6400, "Alvalade": 5800,
    "Alcântara": 5200, "Cascais": 5500, "Estoril": 5800,
    "Porto Centro": 4200, "Almada": 3000, "Oeiras": 4800, "Sintra": 3400,
}

ZONE_SLUGS = {
    "Lisboa Centro": {"imovirtual": "lisboa", "casasapo": "lisboa", "idealista": "lisboa"},
    "Parque das Nações": {"imovirtual": "lisboa/parque-das-nacoes", "casasapo": "lisboa/parque-das-nacoes"},
    "Cascais": {"imovirtual": "cascais", "casasapo": "cascais"},
    "Porto Centro": {"imovirtual": "porto", "casasapo": "porto"},
    "Almada": {"imovirtual": "almada", "casasapo": "almada"},
}

MAX_PAGES_PER_SOURCE = 2
REQUEST_MIN_DELAY = 1.5
REQUEST_MAX_DELAY = 3.5
