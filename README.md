# Russian PII Proxy MVP

Локальный preprocessing-прокси для маскирования персональных данных во входных данных LLM. Сервис поддерживает plain text, Markdown, HTML, TXT, DOCX и PDF с текстовым слоем. OCR и изображения в MVP не обрабатываются.

## Гибридная архитектура

Конвейер состоит из четырёх слоёв:

1. **Regex и валидаторы** находят структурированные PII: email, телефоны, паспорт РФ, СНИЛС, ИНН физлица, банковские карты и IP-адреса. Для ИНН, СНИЛС и карт используются контрольные суммы.
2. **Natasha NER** локально обнаруживает русские ФИО, включая формы в косвенных падежах, а также географические сущности в контексте адреса проживания или регистрации. Организации по умолчанию не маскируются.
3. **Контекстный классификатор ruBERT-tiny2** получает короткое окно вокруг неоднозначного кандидата и классифицирует его как `PII`, `NOT_PII` или `UNCERTAIN`. Модель используется, например, чтобы отличать дату рождения от даты договора.
4. **Policy Engine и anonymizer** маскируют уверенные и сомнительные сущности. Для `UNCERTAIN` применяется fail-safe политика `mask`. Повторяющиеся значения получают одинаковый placeholder внутри документа.

Модель и Natasha работают локально. Во время обработки запросов сервис не скачивает веса и не передаёт текст внешним API.

## Быстрый запуск

```bash
cp .env.example .env
docker compose up --build
```

Swagger: `http://localhost:8000/docs`.

## Подготовка контекстного классификатора

При первой подготовке проекта нужен доступ к Hugging Face для скачивания базовых весов `cointegrated/rubert-tiny2`. После обучения артефакт сохраняется локально в `models/context-rubert-tiny2`.

```bash
python scripts/generate_context_dataset.py --rows 3000
python scripts/train_context_classifier.py --epochs 3 --batch-size 32
```

## Конфигурация

```env
UNCERTAIN_POLICY=mask
NATASHA_ENABLED=true
CONTEXT_CLASSIFIER_ENABLED=true
CONTEXT_MODEL_DIR=models/context-rubert-tiny2
INFERENCE_DEVICE=auto
MASK_ORGANIZATION_PII=false
```

`INFERENCE_DEVICE=auto` выбирает CUDA при её наличии, иначе CPU. Веса классификатора загружаются только из локального каталога.

## API

- `POST /v1/redact` — обработка текста;
- `POST /v1/redact-file` — TXT, DOCX, PDF с текстовым слоем, HTML и Markdown;
- `POST /v1/proxy/chat` — опциональная передача очищенного текста в upstream LLM;
- `GET /health/live`, `GET /health/ready`, `GET /metrics`.

Пример:

```json
{
  "text": "Арендатор: Иванов Петр Сидорович, дата рождения: 12.03.1980",
  "content_type": "text/plain",
  "uncertain_policy": "mask"
}
```

Результат:

```json
{
  "status": "ok",
  "text": "Арендатор: [PERSON_1], дата рождения: [DATE_OF_BIRTH_1]"
}
```

## Тестирование

```bash
pytest
python scripts/run_pipeline.py
```

Синтетические метрики служат проверкой pipeline, но не доказывают качество на произвольных реальных документах. Для production требуется независимый размеченный набор реальных договоров и тендерных документов.
