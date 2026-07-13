# Russian PII Proxy MVP

Локальный preprocessing-прокси для маскирования PII во входных данных LLM. Поддерживает text, Markdown, HTML, TXT, DOCX и PDF с текстовым слоем. Данные организаций по умолчанию не маскируются. Неоднозначные сущности переводятся в `review_required`.

## Запуск
```bash
cp .env.example .env
docker compose up --build
```
Swagger: `http://localhost:8000/docs`.

## Полный прогон на синтетике
```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
make pipeline
```
Артефакты: `data/synthetic/dataset.jsonl`, `reports/metrics.json`, `reports/entity_metrics.csv`.

## API
- `POST /v1/redact`
- `POST /v1/redact-file`
- `POST /v1/proxy/chat`
- `GET /health/live`, `/health/ready`, `/metrics`

## Ограничение метрик
Синтетические шаблоны согласованы с текущими recognizer-ами. Метрики >99% на них подтверждают корректность pipeline, но не доказывают качество на реальных тендерных документах. Для production нужна независимая ручная разметка реальных данных.
