from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from typing import Any, Iterable

from app.detection.entities import Entity
from app.detection.field_context import get_field_context, is_non_pii_date


@dataclass(frozen=True)
class GLiNER2Status:
    enabled: bool
    loaded: bool
    model_name: str
    error: str | None = None


class GLiNER2PII:
    """Lazy local GLiNER2-PII wrapper with exact character spans.

    Model output parsing is defensive because GLiNER2 versions may return
    either dictionaries with explicit spans or text values grouped by label.
    """

    LABELS = [
        "person", "full_name", "date_of_birth", "email", "phone_number",
        "address", "street_address", "passport_number", "national_id_number",
        "tax_id", "payment_card", "bank_account", "ip_address", "username",
    ]
    TYPE_MAP = {
        "person": "PERSON", "full_name": "PERSON", "date_of_birth": "DATE",
        "email": "EMAIL", "phone_number": "PHONE", "address": "ADDRESS",
        "street_address": "ADDRESS", "passport_number": "PASSPORT",
        "national_id_number": "GOVERNMENT_ID", "tax_id": "INN_PERSON",
        "payment_card": "BANK_CARD", "bank_account": "BANK_ACCOUNT",
        "ip_address": "IP_ADDRESS", "username": "USERNAME",
    }

    def __init__(self, enabled: bool, model_name: str, threshold: float = 0.55,
                 device: str = "auto", mask_organizations: bool = False):
        self.enabled = enabled
        self.model_name = model_name
        self.threshold = threshold
        self.device = device
        self.mask_organizations = mask_organizations
        self._model = None
        self._lock = Lock()
        self._error: str | None = None

    @property
    def status(self) -> GLiNER2Status:
        return GLiNER2Status(self.enabled, self._model is not None, self.model_name, self._error)

    def _load(self) -> bool:
        if not self.enabled:
            return False
        if self._model is not None:
            return True
        with self._lock:
            if self._model is not None:
                return True
            try:
                from gliner2 import GLiNER2
                kwargs: dict[str, Any] = {}
                if self.device == "cuda":
                    kwargs["map_location"] = "cuda"
                self._model = GLiNER2.from_pretrained(self.model_name, **kwargs)
                return True
            except Exception as exc:  # pragma: no cover - depends on model/runtime
                self._error = f"{type(exc).__name__}: {exc}"
                return False

    @staticmethod
    def _find_all(text: str, value: str) -> Iterable[tuple[int, int]]:
        pos = 0
        while value and (idx := text.find(value, pos)) >= 0:
            yield idx, idx + len(value)
            pos = idx + len(value)

    def _iter_raw(self, text: str, result: dict[str, Any]) -> Iterable[tuple[str, int, int, float]]:
        groups = result.get("entities", result)
        if not isinstance(groups, dict):
            return
        for label, values in groups.items():
            if not isinstance(values, list):
                continue
            for item in values:
                if isinstance(item, str):
                    for start, end in self._find_all(text, item):
                        yield label, start, end, self.threshold
                elif isinstance(item, dict):
                    value = item.get("text") or item.get("value") or item.get("span")
                    start = item.get("start")
                    end = item.get("end")
                    score = float(item.get("confidence", item.get("score", self.threshold)))
                    if isinstance(start, int) and isinstance(end, int):
                        yield label, start, end, score
                    elif isinstance(value, str):
                        for s, e in self._find_all(text, value):
                            yield label, s, e, score

    def detect(self, text: str) -> list[Entity]:
        if not self._load():
            return []
        result = self._model.extract_entities(
            text, self.LABELS, threshold=self.threshold,
            include_confidence=True, include_spans=True,
        )
        entities: list[Entity] = []
        for label, start, end, score in self._iter_raw(text, result):
            entity_type = self.TYPE_MAP.get(label)
            if not entity_type or end <= start:
                continue
            ctx = get_field_context(text, start, end)
            if entity_type == "DATE" and is_non_pii_date(ctx):
                continue
            if entity_type in {"INN_PERSON", "ADDRESS", "PHONE", "EMAIL"} and ctx.organization_scope and not ctx.person_scope:
                continue
            entities.append(Entity(entity_type, start, end, score, f"GLiNER2-PII {label} ({score:.3f})"))
        return entities
