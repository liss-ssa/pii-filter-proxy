import re
from app.config import get_settings
from app.detection.entities import Entity
from app.detection.validators import inn_ok, snils_ok, luhn_ok

class DetectionEngine:
    EMAIL=re.compile(r"(?<![\w.+-])([A-Za-z0-9][A-Za-z0-9._%+-]{0,63}@[A-Za-z0-9.-]+\.[A-Za-z]{2,})(?![\w-])")
    PHONE=re.compile(r"(?<!\d)(?:\+7|8)[\s\-(]*(?:\d[\s\-()]*){10}(?!\d)")
    PASSPORT=re.compile(r"(?i)\bпаспорт(?:\s+гражданина\s+рф)?\s*(?:серии\s*)?(\d{2}\s?\d{2})\s*(?:№|номер)?\s*(\d{6})\b")
    SNILS=re.compile(r"(?i)(?:снилс\s*[:№]?\s*)?(?<!\d)(\d{3}[- ]?\d{3}[- ]?\d{3}[ -]?\d{2})(?!\d)")
    INN=re.compile(r"(?i)(?:инн\s*[:№]?\s*)?(?<!\d)(\d{10}|\d{12})(?!\d)")
    CARD=re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")
    DOB_NUM=re.compile(r"(?<!\d)(0[1-9]|[12]\d|3[01])[./-](0[1-9]|1[0-2])[./-](19\d{2}|20\d{2})(?!\d)")
    FULL_NAME=re.compile(r"(?:Гражданин\s+)?(?P<name>[А-ЯЁ][а-яё-]{1,30}\s+[А-ЯЁ][а-яё-]{1,30}\s+[А-ЯЁ][а-яё-]{1,30})\b")
    ADDRESS=re.compile(r"(?i)(?:адрес(?: регистрации| проживания)?\s*[:\-]?\s*)([^\n;]{8,140}?)(?=,\s*(?:банковская карта|телефон|email|паспорт)|[;\n]|$)")
    IP=re.compile(r"(?<!\d)(?:25[0-5]|2[0-4]\d|1?\d?\d)(?:\.(?:25[0-5]|2[0-4]\d|1?\d?\d)){3}(?!\d)")
    CONTRACT_DATE_WORDS=("договор", "вступает в силу", "действует до", "срок", "оплат", "ежемесячно", "поставк", "исполнен", "протокол", "заседание", "составлен", "назначено")
    DOB_WORDS=("дата рождения", "родился", "родилась", "года рождения", "д.р.")
    PERSON_CONTEXT=("арендатор", "физическое лицо", "гражданин", "представитель", "заказчик:", "исполнитель:", "фио", "подписант")

    def __init__(self): self.settings=get_settings()

    def _add(self,out,e):
        if e.end>e.start: out.append(e)

    def detect(self,text:str)->list[Entity]:
        out=[]; low=text.lower()
        for m in self.EMAIL.finditer(text): self._add(out,Entity("EMAIL",m.start(1),m.end(1),.995,"deterministic email pattern"))
        for m in self.PHONE.finditer(text): self._add(out,Entity("PHONE",m.start(),m.end(),.97,"Russian phone pattern"))
        for m in self.PASSPORT.finditer(text): self._add(out,Entity("PASSPORT",m.start(),m.end(),.995,"passport keyword and number pattern"))
        for m in self.SNILS.finditer(text):
            if snils_ok(m.group(1)): self._add(out,Entity("SNILS",m.start(),m.end(),.995,"SNILS checksum"))
        for m in self.INN.finditer(text):
            if inn_ok(m.group(1)):
                context=low[max(0,m.start()-40):m.start()]
                typ="INN_PERSON" if len(re.sub(r'\D','',m.group(1)))==12 else "INN_ORG"
                if typ=="INN_PERSON" or self.settings.mask_organization_pii:
                    self._add(out,Entity(typ,m.start(),m.end(),.99,"INN checksum and policy"))
        for m in self.CARD.finditer(text):
            raw=m.group()
            if luhn_ok(raw): self._add(out,Entity("BANK_CARD",m.start(),m.end(),.995,"Luhn checksum"))
        for m in self.IP.finditer(text): self._add(out,Entity("IP_ADDRESS",m.start(),m.end(),.97,"IPv4 pattern"))
        for m in self.DOB_NUM.finditer(text):
            w=low[max(0,m.start()-90):min(len(low),m.end()+60)]
            if any(k in w for k in self.DOB_WORDS):
                self._add(out,Entity("DATE_OF_BIRTH",m.start(),m.end(),.985,"birth-date context"))
            elif any(k in w for k in self.CONTRACT_DATE_WORDS):
                pass
            else:
                self._add(out,Entity("DATE",m.start(),m.end(),.48,"ambiguous date"))
        for m in self.FULL_NAME.finditer(text):
            ns, ne = m.start("name"), m.end("name")
            w=low[max(0,ns-100):min(len(low),ne+80)]
            # avoid common document headings and legal prose
            if any(k in w for k in self.PERSON_CONTEXT) or any(k in w for k in self.DOB_WORDS) or "паспорт" in w:
                self._add(out,Entity("PERSON",ns,ne,.93,"Russian full-name pattern with contextual score"))
        for m in self.ADDRESS.finditer(text):
            candidate=m.group(1).strip(' ,.')
            s=m.start(1); e=s+len(candidate)
            w=low[max(0,m.start()-80):m.end()]
            if any(k in w for k in ("регистрац", "прожив", "физичес", "граждан")):
                self._add(out,Entity("ADDRESS",s,e,.90,"personal-address context"))
        return self._resolve(out)

    def _resolve(self,entities):
        # prefer higher score and longer span; remove overlapping duplicates
        ordered=sorted(entities,key=lambda e:(-e.score,-(e.end-e.start),e.start))
        selected=[]
        for e in ordered:
            if not any(e.start < x.end and x.start < e.end for x in selected): selected.append(e)
        return sorted(selected,key=lambda e:(e.start,e.end))
