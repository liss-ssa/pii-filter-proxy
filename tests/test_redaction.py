from app.detection.engine import DetectionEngine
from app.anonymization.replacer import replace_entities
eng=DetectionEngine()
def redact(t):
 e=[x for x in eng.detect(t) if x.score>=.8]; return replace_entities(t,e)[0],e

def test_contract_dates_not_pii():
 t='Настоящий Договор вступает в силу с 01.09.2025 и действует до 31.08.2026.'; out,e=redact(t); assert out==t; assert not e

def test_personal_block():
 t='Арендатор: Иванов Петр Сидорович, дата рождения: 12.03.1980, паспорт серии 4510 №123456, email ivan@test.ru'
 out,e=redact(t)
 for ph in ['[PERSON_1]','[DATE_1]','[PASSPORT_1]','[EMAIL_1]']: assert ph in out

def test_stable_placeholder():
 out,_=redact('Email: a@test.ru. Повторно a@test.ru.'); assert out.count('[EMAIL_1]')==2

def test_ambiguous_document_date_is_not_masked():
 e=eng.detect('Дата: 12.03.1980. Документ подписан сторонами.'); assert not any(x.entity_type in {'DATE'} for x in e)
