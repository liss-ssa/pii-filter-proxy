from __future__ import annotations

from dataclasses import dataclass
from threading import Lock

from app.detection.entities import Entity


@dataclass(frozen=True)
class NatashaStatus:
    enabled: bool
    loaded: bool
    error: str | None = None


class NatashaNER:
    """Lazy local Natasha NER wrapper.

    Natasha emits PER/LOC/ORG. Organizations are ignored unless explicitly
    enabled by policy. LOC spans become ADDRESS only in personal-address context.
    """

    PERSON_CONTEXT = (
        "арендатор", "гражданин", "физическое лицо", "представитель",
        "фио", "подписант", "дата рождения", "паспорт", "телефон", "email",
    )
    ADDRESS_CONTEXT = (
        "адрес регистрации", "адрес проживания", "зарегистрирован",
        "проживает", "место жительства", "фактический адрес",
    )

    def __init__(self, enabled: bool = True, mask_organizations: bool = False):
        self.enabled = enabled
        self.mask_organizations = mask_organizations
        self._segmenter = None
        self._emb = None
        self._tagger = None
        self._doc_cls = None
        self._lock = Lock()
        self._error: str | None = None

    @property
    def status(self) -> NatashaStatus:
        return NatashaStatus(self.enabled, self._tagger is not None, self._error)

    def _load(self) -> bool:
        if not self.enabled:
            return False
        if self._tagger is not None:
            return True
        with self._lock:
            if self._tagger is not None:
                return True
            try:
                from natasha import Doc, NewsEmbedding, NewsNERTagger, Segmenter

                self._doc_cls = Doc
                self._segmenter = Segmenter()
                self._emb = NewsEmbedding()
                self._tagger = NewsNERTagger(self._emb)
                return True
            except Exception as exc:  # pragma: no cover - environment dependent
                self._error = f"{type(exc).__name__}: {exc}"
                return False

    def detect(self, text: str) -> list[Entity]:
        if not self._load():
            return []
        assert self._doc_cls is not None and self._segmenter is not None and self._tagger is not None
        doc = self._doc_cls(text)
        doc.segment(self._segmenter)
        doc.tag_ner(self._tagger)
        low = text.casefold()
        result: list[Entity] = []
        for span in doc.spans:
            window = low[max(0, span.start - 120): min(len(low), span.stop + 100)]
            if span.type == "PER":
                score = 0.94 if any(key in window for key in self.PERSON_CONTEXT) else 0.74
                result.append(Entity("PERSON", span.start, span.stop, score, "Natasha PER NER"))
            elif span.type == "LOC" and any(key in window for key in self.ADDRESS_CONTEXT):
                result.append(Entity("ADDRESS", span.start, span.stop, 0.88, "Natasha LOC in personal-address context"))
            elif span.type == "ORG" and self.mask_organizations:
                result.append(Entity("ORGANIZATION", span.start, span.stop, 0.88, "Natasha ORG and organization masking policy"))
        return result
