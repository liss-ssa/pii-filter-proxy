from app.detection.engine import DetectionEngine


def test_regex_finds_person_in_personal_context():
    engine = DetectionEngine()
    text = "Арендатор: Петрова Анна Сергеевна, паспорт указан в приложении."
    entities = engine.detect(text)
    assert any(e.entity_type == "PERSON" and text[e.start:e.end] == "Петрова Анна Сергеевна" for e in entities)


def test_ambiguous_document_date_is_not_masked():
    engine = DetectionEngine()
    entities = engine.detect("Дата размещения\n12.03.1980\nДокумент опубликован в реестре.")
    assert not any(e.entity_type in {"DATE"} for e in entities)


def test_ambiguous_person_date_is_fail_safe_maskable():
    engine = DetectionEngine()
    entities = engine.detect("Физическое лицо. Дата: 12.03.1980. Дополнительный контекст отсутствует.")
    assert any(e.entity_type in {"DATE"} and e.score >= 0.35 for e in entities)
