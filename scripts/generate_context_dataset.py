from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

NAMES = [
    "Иванов Петр Сидорович", "Петрова Анна Сергеевна", "Сидоров Алексей Иванович",
    "Кузнецова Мария Андреевна", "Смирнов Дмитрий Олегович", "Орлова Елена Викторовна",
]
PII_DATE = [
    "Арендатор {name}, дата рождения: {date}, паспорт указан ниже.",
    "ФИО: {name}. Родился {date} в городе Москве.",
    "Сведения о физическом лице: {name}, {date} года рождения.",
    "Представитель {name}; д.р. {date}; телефон указан в анкете.",
]
NOT_PII_DATE = [
    "Договор вступает в силу {date} и действует до окончания обязательств.",
    "Срок поставки установлен до {date}.",
    "Протокол составлен {date}, заседание завершено в тот же день.",
    "Оплата должна быть произведена не позднее {date}.",
    "Дата публикации извещения: {date}.",
]
UNCERTAIN_DATE = [
    "Дата: {date}. Документ подписан сторонами.",
    "В анкете указано: {date}.",
    "Запись от {date} находится в разделе дополнительных сведений.",
    "Сведения обновлены: {date}.",
]
PII_PERSON = [
    "Арендатор: {name}, паспорт и дата рождения указаны далее.",
    "Физическое лицо {name} подписало согласие на обработку данных.",
    "Представитель по доверенности: {name}, телефон указан в приложении.",
]
NOT_PII_PERSON = [
    "Наименование документа: План закупок Российской Федерации.",
    "Система Электронный Бюджет используется заказчиком.",
    "Компания Северный Ветер выполнила поставку оборудования.",
]


def date(rng: random.Random, personal: bool) -> str:
    year = rng.randint(1950, 2005) if personal else rng.randint(2024, 2032)
    return f"{rng.randint(1, 28):02d}.{rng.randint(1, 12):02d}.{year}"


def build(rows: int, seed: int) -> list[dict]:
    rng = random.Random(seed)
    items: list[dict] = []
    labels = ["PII", "NOT_PII", "UNCERTAIN"]
    for i in range(rows):
        label = labels[i % 3]
        entity_type = "DATE" if rng.random() < 0.8 else "PERSON"
        name = rng.choice(NAMES)
        if entity_type == "DATE":
            d = date(rng, label == "PII")
            templates = PII_DATE if label == "PII" else NOT_PII_DATE if label == "NOT_PII" else UNCERTAIN_DATE
            text = rng.choice(templates).format(name=name, date=d)
            target = d
        else:
            if label == "PII":
                text = rng.choice(PII_PERSON).format(name=name)
                target = name
            elif label == "NOT_PII":
                text = rng.choice(NOT_PII_PERSON)
                target = text.split(":", 1)[-1].strip().rstrip(".")
            else:
                text = f"Указано имя {name}. Дополнительный контекст отсутствует."
                target = name
        start = text.index(target)
        marked = f"[TYPE] {entity_type} [LEFT] {text[:start]} [TARGET] {target} [RIGHT] {text[start + len(target):]}"
        items.append({"id": f"ctx_{i:06d}", "text": marked, "label": label})
    rng.shuffle(items)
    return items


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=3000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--output", default="data/context/context_dataset.jsonl")
    args = ap.parse_args()
    rows = build(args.rows, args.seed)
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")
    print(json.dumps({"rows": len(rows), "output": str(path)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
