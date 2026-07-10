"""Modelo de dados normalizado — formato único para todas as fontes."""
from dataclasses import dataclass, field, asdict
from typing import Optional
from datetime import datetime, timezone
import hashlib


@dataclass
class Listing:
    portal: str
    category: str
    external_id: str
    title: str
    price: Optional[float]
    market_estimate: Optional[float]
    currency: str
    url: str
    zone: Optional[str] = None
    area_m2: Optional[float] = None
    posted_date: Optional[str] = None
    scraped_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    details: dict = field(default_factory=dict)
    is_real: bool = True
    discount_pct: float = 0.0
    score: int = 0
    confidence: float = 0.85

    def compute_score(self):
        if not self.price or not self.market_estimate or self.market_estimate <= 0:
            self.discount_pct = 0
            self.score = 0
            return
        disc = (self.market_estimate - self.price) / self.market_estimate
        self.discount_pct = round(max(0, disc) * 100, 1)
        self.score = min(97, round(self.discount_pct * self.confidence * 1.8))

    def stable_id(self) -> str:
        return hashlib.sha256(self.url.encode()).hexdigest()[:16]

    def to_dict(self) -> dict:
        d = asdict(self)
        d["id"] = self.stable_id()
        return d
