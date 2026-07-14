from app.detection.engine import DetectionEngine


def test_natasha_finds_inflected_person():
    engine = DetectionEngine()
    text = "Договор подписан арендатором Петровой Анной Сергеевной, паспорт указан в приложении."
    entities = engine.detect(text)
    assert any(e.entity_type == "PERSON" and "Петровой Анной Сергеевной" == text[e.start:e.end] for e in entities)


def test_ambiguous_date_is_maskable_fail_safe():
    engine = DetectionEngine()
    entities = engine.detect("Дата: 12.03.1980. Дополнительный контекст отсутствует.")
    assert any(e.entity_type == "DATE" and e.score >= 0.35 for e in entities)
