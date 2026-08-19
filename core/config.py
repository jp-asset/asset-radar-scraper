"""Configuração partilhada: zonas, preços de referência."""

ZONE_PRICES_DEFAULT = {
    "Lisboa Centro": 7200, "Parque das Nações": 6400, "Alvalade": 5800,
    "Alcântara": 5200, "Cascais": 5500, "Estoril": 5800,
    "Porto Centro": 4200, "Almada": 3000, "Oeiras": 4800, "Sintra": 3400,
}

ZONE_SLUGS = {
    "Lisboa Centro": "lisboa", "Parque das Nações": "lisboa/parque-das-nacoes",
    "Alvalade": "lisboa/alvalade", "Alcântara": "lisboa/alcantara",
    "Cascais": "cascais", "Estoril": "cascais/estoril",
    "Porto Centro": "porto", "Almada": "almada",
    "Oeiras": "oeiras", "Sintra": "sintra",
}
