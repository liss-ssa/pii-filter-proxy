# Hybrid detector update

Реализованы:

- локальный Natasha NER для русских `PER`, `LOC` и опциональных `ORG`;
- локальный inference-wrapper для классификатора `cointegrated/rubert-tiny2`;
- классы контекста `PII`, `NOT_PII`, `UNCERTAIN`;
- генератор синтетического датасета контекстов;
- скрипт fine-tuning и сохранения локального артефакта;
- fail-safe политика `mask` для сомнительных сущностей;
- автоматический fallback на правила, если модель ещё не обучена;
- CUDA/CPU auto-selection;
- тесты Natasha и fail-safe pipeline.

В среде сборки загрузка весов Hugging Face была недоступна из-за DNS, поэтому бинарный обученный артефакт модели не включён. Он воспроизводимо создаётся локально командами из README.
