"""Download and warm up local inference models once.

Run on a machine with internet access. Later inference remains local.
"""
from app.config import get_settings
from app.detection.engine import DetectionEngine


def main() -> None:
    settings = get_settings()
    engine = DetectionEngine()
    sample = "Физическое лицо: Иванов Иван Иванович, email ivanov@example.ru."
    entities = engine.detect(sample)
    print({
        "ner_backend": settings.ner_backend,
        "gliner2": engine.gliner.status.__dict__,
        "context_classifier_loaded": engine.classifier.loaded,
        "entities": [e.__dict__ for e in entities],
    })
    if settings.gliner2_enabled and not engine.gliner.status.loaded:
        raise SystemExit(f"GLiNER2 model was not loaded: {engine.gliner.status.error}")


if __name__ == "__main__":
    main()
