# Context classifier artifact

Этот каталог заполняется командой:

```bash
python scripts/generate_context_dataset.py --rows 3000
python scripts/train_context_classifier.py --epochs 3 --batch-size 32
```

Базовая модель: `cointegrated/rubert-tiny2`. Итоговый классификатор имеет классы `NOT_PII`, `PII`, `UNCERTAIN`.
