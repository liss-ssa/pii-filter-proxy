from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class FieldContext:
    section: str | None
    field: str | None
    window: str
    organization_scope: bool
    person_scope: bool


ORG_SCOPE = (
    "организация", "юридическ", "поставщик", "исполнитель", "заказчик",
    "общество с ограниченной ответственностью", "ооо ", "ао ", "пао ", "гуп ",
    "налоговом органе", "кпп", "огрн", "ктру", "окпд", "оквэд",
)
PERSON_SCOPE = (
    "физическое лицо", "гражданин", "арендатор", "сотрудник", "представитель",
    "получатель", "контактное лицо", "дата рождения", "паспорт", "снилс",
    "место жительства", "адрес регистрации", "адрес проживания",
)

NON_PII_DATE_FIELDS = (
    "дата размещения", "дата публикации", "дата изменения", "дата заключения",
    "дата подписания", "дата документа", "дата постановки на учет",
    "дата регистрации организации", "срок действия", "период", "действует с",
    "действует до", "дата оплаты", "дата поставки", "дата исполнения",
)
DOB_FIELDS = ("дата рождения", "родился", "родилась", "год рождения", "д.р.")
DOCUMENT_DATE_CONTEXT = (
    "документ подписан", "подписан сторонами", "договор подписан",
    "контракт подписан", "акт подписан", "приказ подписан",
    "документ составлен", "документ оформлен",
)

IDENTIFIER_FIELDS = {
    "огрн": "OGRN",
    "кпп": "KPP",
    "инн": "INN",
    "ктру": "KTRU",
    "окпд": "OKPD2",
    "оквэд": "OKVED",
    "номер контракта": "CONTRACT_NUMBER",
    "номер договора": "CONTRACT_NUMBER",
}


def _lines_before(text: str, start: int, limit: int = 8) -> list[str]:
    return [line.strip() for line in text[:start].splitlines()[-limit:] if line.strip()]


def get_field_context(text: str, start: int, end: int) -> FieldContext:
    lines = _lines_before(text, start)
    field = lines[-1] if lines else None
    section = None
    for line in reversed(lines[:-1]):
        low = line.casefold()
        if low.startswith(("информация о", "сведения о", "общая информация", "реквизиты")):
            section = line
            break
    left = max(0, start - 300)
    right = min(len(text), end + 180)
    window = text[left:right].casefold()
    scope_text = " ".join(lines[-5:]).casefold() + " " + window
    return FieldContext(
        section=section,
        field=field,
        window=window,
        organization_scope=any(x in scope_text for x in ORG_SCOPE),
        person_scope=any(x in scope_text for x in PERSON_SCOPE),
    )


def field_identifier_type(ctx: FieldContext) -> str | None:
    value = (ctx.field or "").casefold()
    for marker, entity_type in IDENTIFIER_FIELDS.items():
        if marker in value:
            return entity_type
    return None


def is_non_pii_date(ctx: FieldContext) -> bool:
    probe = f"{ctx.field or ''} {ctx.section or ''} {ctx.window}".casefold()
    has_document_context = any(x in probe for x in DOCUMENT_DATE_CONTEXT)
    has_non_pii_field = any(x in probe for x in NON_PII_DATE_FIELDS)
    has_birth_context = any(x in probe for x in DOB_FIELDS)
    return (has_non_pii_field or has_document_context) and not has_birth_context


def is_birth_date(ctx: FieldContext) -> bool:
    probe = f"{ctx.field or ''} {ctx.window}".casefold()
    return any(x in probe for x in DOB_FIELDS)


def looks_like_catalog_code(text: str, start: int, end: int, ctx: FieldContext) -> bool:
    value = text[start:end]
    probe = f"{ctx.field or ''} {ctx.section or ''} {ctx.window}".casefold()
    if any(x in probe for x in ("ктру", "окпд", "код позиции", "код товара", "классификатор")):
        return True
    return bool(re.match(r"^\d{2}(?:\.\d{2}){2}\.\d{3}(?:-\d{8})?$", value))


def has_ip_context(ctx: FieldContext) -> bool:
    return any(x in ctx.window for x in ("ip-адрес", "ip адрес", "ipv4", "адрес узла", "сервер", "источник подключения"))
