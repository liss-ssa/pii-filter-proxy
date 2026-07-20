from app.detection.engine import DetectionEngine


def types_and_values(text: str):
    return [(e.entity_type, text[e.start:e.end]) for e in DetectionEngine().detect(text)]


def test_ogrn_is_not_bank_card():
    text = "Информация о поставщике\nОГРН\n1101690003590"
    assert not any(t == "BANK_CARD" for t, _ in types_and_values(text))


def test_ktru_is_not_ip():
    text = "Код позиции КТРУ\tНаименование\n28.99.39.190\tОборудование\n26.30.50.152-00000001\tТурникет"
    assert not any(t == "IP_ADDRESS" for t, _ in types_and_values(text))


def test_real_ip_with_explicit_context_is_masked():
    text = "IP-адрес рабочего места: 192.168.10.24"
    assert ("IP_ADDRESS", "192.168.10.24") in types_and_values(text)


def test_tax_registration_date_is_not_birth_date():
    text = "Информация о поставщике\nДата постановки на учет в налоговом органе\n24.12.2021"
    assert not any(t in {"DATE"} for t, _ in types_and_values(text))


def test_birth_date_is_masked():
    text = "Арендатор: Иванов Петр Сидорович\nДата рождения\n12.03.1980"
    values = types_and_values(text)
    assert ("DATE", "12.03.1980") in values


def test_all_masked_dates_use_canonical_date_type():
    text = "Иванов Иван Иванович, дата рождения 12.03.1980."
    entities = DetectionEngine().detect(text)
    date_entities = [entity for entity in entities if entity.start == text.index("12.03.1980")]
    assert date_entities
    assert all(entity.entity_type == "DATE" for entity in date_entities)
    assert all(entity.entity_type != "DATE_OF_BIRTH" for entity in entities)
