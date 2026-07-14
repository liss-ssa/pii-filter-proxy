from __future__ import annotations

import re

from app.config import get_settings
from app.detection.context_classifier import (
    LABEL_NOT_PII,
    LABEL_PII,
    LABEL_UNCERTAIN,
    ContextClassifier,
)
from app.detection.entities import Entity
from app.detection.natasha_ner import NatashaNER
from app.detection.validators import inn_ok, luhn_ok, snils_ok


class DetectionEngine:
    EMAIL = re.compile(r"(?<![\w.+-])([A-Za-z0-9][A-Za-z0-9._%+-]{0,63}@[A-Za-z0-9.-]+\.[A-Za-z]{2,})(?![\w-])")
    PHONE = re.compile(r"(?<!\d)(?:\+7|8)[\s\-(]*(?:\d[\s\-()]*){10}(?!\d)")
    PASSPORT = re.compile(r"(?i)\bпаспорт(?:\s+гражданина\s+рф)?\s*(?:серии\s*)?(\d{2}\s?\d{2})\s*(?:№|номер)?\s*(\d{6})\b")
    SNILS = re.compile(r"(?i)(?:снилс\s*[:№]?\s*)?(?<!\d)(\d{3}[- ]?\d{3}[- ]?\d{3}[ -]?\d{2})(?!\d)")
    INN = re.compile(r"(?i)(?:инн\s*[:№]?\s*)?(?<!\d)(\d{10}|\d{12})(?!\d)")
    CARD = re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")
    DOB_NUM = re.compile(r"(?<!\d)(0[1-9]|[12]\d|3[01])[./-](0[1-9]|1[0-2])[./-](19\d{2}|20\d{2})(?!\d)")
    FULL_NAME = re.compile(r"(?:Гражданин\s+)?(?P<name>[А-ЯЁ][а-яё-]{1,30}\s+[А-ЯЁ][а-яё-]{1,30}\s+[А-ЯЁ][а-яё-]{1,30})\b")
    ADDRESS = re.compile(r"(?i)(?:адрес(?: регистрации| проживания)?\s*[:\-]?\s*)([^\n;]{8,140}?)(?=,\s*(?:банковская карта|телефон|email|паспорт)|[;\n]|$)")
    IP = re.compile(r"(?<!\d)(?:25[0-5]|2[0-4]\d|1?\d?\d)(?:\.(?:25[0-5]|2[0-4]\d|1?\d?\d)){3}(?!\d)")

    CONTRACT_DATE_WORDS = (
        "договор", "вступает в силу", "действует до", "срок", "оплат", "ежемесячно",
        "поставк", "исполнен", "протокол", "заседание", "составлен", "назначено",
        "публикац", "извещен",
    )
    DOB_WORDS = ("дата рождения", "родился", "родилась", "года рождения", "д.р.")
    PERSON_CONTEXT = (
        "арендатор", "физическое лицо", "гражданин", "представитель", "заказчик:",
        "исполнитель:", "фио", "подписант",
    )

    def __init__(self):
        self.settings = get_settings()
        self.ner = NatashaNER(
            enabled=self.settings.natasha_enabled,
            mask_organizations=self.settings.mask_organization_pii,
        )
        self.classifier = ContextClassifier(
            model_dir=self.settings.context_model_dir,
            enabled=self.settings.context_classifier_enabled,
            device=self.settings.inference_device,
            max_length=self.settings.context_max_length,
        )

    @staticmethod
    def _add(out: list[Entity], entity: Entity) -> None:
        if entity.end > entity.start:
            out.append(entity)

    def _classify_candidate(self, text: str, candidate: Entity) -> Entity | None:
        prediction = self.classifier.predict(text, candidate)
        if prediction is None:
            # Safe deterministic fallback. Ambiguous candidates remain maskable.
            return candidate
        label, confidence = prediction
        if label == LABEL_NOT_PII and confidence >= self.settings.context_not_pii_threshold:
            return None
        if label == LABEL_PII:
            entity_type = "DATE_OF_BIRTH" if candidate.entity_type == "DATE" else candidate.entity_type
            score = max(self.settings.redact_threshold, confidence)
            return Entity(entity_type, candidate.start, candidate.end, score, f"ruBERT-tiny2 context: PII ({confidence:.3f})")
        if label == LABEL_UNCERTAIN:
            return Entity(candidate.entity_type, candidate.start, candidate.end, self.settings.uncertain_mask_score, f"ruBERT-tiny2 context: UNCERTAIN ({confidence:.3f}); fail-safe mask")
        # Low-confidence NOT_PII is still masked under fail-safe policy.
        return Entity(candidate.entity_type, candidate.start, candidate.end, self.settings.uncertain_mask_score, f"ruBERT-tiny2 low confidence ({confidence:.3f}); fail-safe mask")

    def detect(self, text: str) -> list[Entity]:
        out: list[Entity] = []
        low = text.casefold()

        for m in self.EMAIL.finditer(text):
            self._add(out, Entity("EMAIL", m.start(1), m.end(1), .995, "deterministic email pattern"))
        for m in self.PHONE.finditer(text):
            self._add(out, Entity("PHONE", m.start(), m.end(), .97, "Russian phone pattern"))
        for m in self.PASSPORT.finditer(text):
            self._add(out, Entity("PASSPORT", m.start(), m.end(), .995, "passport keyword and number pattern"))
        for m in self.SNILS.finditer(text):
            if snils_ok(m.group(1)):
                self._add(out, Entity("SNILS", m.start(), m.end(), .995, "SNILS checksum"))
        for m in self.INN.finditer(text):
            if inn_ok(m.group(1)):
                entity_type = "INN_PERSON" if len(re.sub(r"\D", "", m.group(1))) == 12 else "INN_ORG"
                if entity_type == "INN_PERSON" or self.settings.mask_organization_pii:
                    self._add(out, Entity(entity_type, m.start(), m.end(), .99, "INN checksum and policy"))
        for m in self.CARD.finditer(text):
            if luhn_ok(m.group()):
                self._add(out, Entity("BANK_CARD", m.start(), m.end(), .995, "Luhn checksum"))
        for m in self.IP.finditer(text):
            self._add(out, Entity("IP_ADDRESS", m.start(), m.end(), .97, "IPv4 pattern"))

        # Dates are first resolved by high-precision context, then by ruBERT.
        for m in self.DOB_NUM.finditer(text):
            window = low[max(0, m.start() - 100): min(len(low), m.end() + 80)]
            if any(key in window for key in self.DOB_WORDS):
                self._add(out, Entity("DATE_OF_BIRTH", m.start(), m.end(), .985, "birth-date context"))
            elif any(key in window for key in self.CONTRACT_DATE_WORDS):
                continue
            else:
                candidate = Entity("DATE", m.start(), m.end(), .48, "ambiguous date candidate")
                classified = self._classify_candidate(text, candidate)
                if classified is not None:
                    self._add(out, classified)

        # Deterministic person fallback remains useful when Natasha is unavailable.
        for m in self.FULL_NAME.finditer(text):
            start, end = m.start("name"), m.end("name")
            window = low[max(0, start - 100): min(len(low), end + 80)]
            if any(key in window for key in self.PERSON_CONTEXT) or any(key in window for key in self.DOB_WORDS) or "паспорт" in window:
                self._add(out, Entity("PERSON", start, end, .93, "Russian full-name pattern with contextual score"))

        for m in self.ADDRESS.finditer(text):
            candidate = m.group(1).strip(" ,.")
            start = m.start(1)
            end = start + len(candidate)
            window = low[max(0, m.start() - 80): m.end()]
            if any(key in window for key in ("регистрац", "прожив", "физичес", "граждан")):
                self._add(out, Entity("ADDRESS", start, end, .90, "personal-address context"))

        # Natasha adds inflected names and locations not covered by regex.
        for entity in self.ner.detect(text):
            if entity.score >= self.settings.redact_threshold:
                self._add(out, entity)
            else:
                classified = self._classify_candidate(text, entity)
                if classified is not None:
                    self._add(out, classified)

        return self._resolve(out)

    @staticmethod
    def _resolve(entities: list[Entity]) -> list[Entity]:
        ordered = sorted(entities, key=lambda e: (-e.score, -(e.end - e.start), e.start))
        selected: list[Entity] = []
        for entity in ordered:
            if not any(entity.start < other.end and other.start < entity.end for other in selected):
                selected.append(entity)
        return sorted(selected, key=lambda e: (e.start, e.end))
