from __future__ import annotations

import json
from pathlib import Path
from threading import Lock

from app.detection.entities import Entity

LABEL_PII = "PII"
LABEL_NOT_PII = "NOT_PII"
LABEL_UNCERTAIN = "UNCERTAIN"


class ContextClassifier:
    """Local ruBERT-tiny2 sequence classifier for candidate context.

    The classifier is loaded lazily from a local directory. It never downloads
    weights during request processing. If the artifact is absent, the caller can
    use deterministic fallback rules.
    """

    def __init__(self, model_dir: str, enabled: bool = True, device: str = "auto", max_length: int = 192):
        self.model_dir = Path(model_dir)
        self.enabled = enabled
        self.device_requested = device
        self.max_length = max_length
        self._tokenizer = None
        self._model = None
        self._torch = None
        self._device = "cpu"
        self._lock = Lock()
        self._error: str | None = None

    @property
    def loaded(self) -> bool:
        return self._model is not None

    @property
    def error(self) -> str | None:
        return self._error

    def _load(self) -> bool:
        if not self.enabled:
            return False
        if self._model is not None:
            return True
        if not (self.model_dir / "config.json").exists():
            self._error = f"model artifact not found: {self.model_dir}"
            return False
        with self._lock:
            if self._model is not None:
                return True
            try:
                import torch
                from transformers import AutoModelForSequenceClassification, AutoTokenizer

                self._torch = torch
                self._tokenizer = AutoTokenizer.from_pretrained(self.model_dir, local_files_only=True)
                self._model = AutoModelForSequenceClassification.from_pretrained(self.model_dir, local_files_only=True)
                requested = self.device_requested.casefold()
                use_cuda = requested in {"cuda", "auto"} and torch.cuda.is_available()
                self._device = "cuda" if use_cuda else "cpu"
                self._model.to(self._device)
                self._model.eval()
                return True
            except Exception as exc:  # pragma: no cover - environment dependent
                self._error = f"{type(exc).__name__}: {exc}"
                return False

    @staticmethod
    def build_input(text: str, candidate: Entity, radius: int = 160) -> str:
        left = text[max(0, candidate.start - radius): candidate.start]
        target = text[candidate.start: candidate.end]
        right = text[candidate.end: min(len(text), candidate.end + radius)]
        return f"[TYPE] {candidate.entity_type} [LEFT] {left} [TARGET] {target} [RIGHT] {right}"

    def predict(self, text: str, candidate: Entity) -> tuple[str, float] | None:
        if not self._load():
            return None
        assert self._tokenizer is not None and self._model is not None and self._torch is not None
        encoded = self._tokenizer(
            self.build_input(text, candidate),
            return_tensors="pt",
            truncation=True,
            max_length=self.max_length,
        )
        encoded = {k: v.to(self._device) for k, v in encoded.items()}
        with self._torch.inference_mode():
            logits = self._model(**encoded).logits[0]
            probs = self._torch.softmax(logits, dim=-1)
        idx = int(probs.argmax().item())
        config = self._model.config
        label = config.id2label.get(idx, str(idx))
        return label, float(probs[idx].item())
