import argparse,json,random,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

SURNAMES=['Иванов','Петров','Сидоров','Смирнов','Кузнецов','Попов','Васильев','Соколов','Михайлов','Новиков']
NAMES=['Иван','Петр','Алексей','Сергей','Дмитрий','Андрей','Николай','Михаил','Максим','Владимир']
PATR=['Иванович','Петрович','Алексеевич','Сергеевич','Дмитриевич','Андреевич','Николаевич','Михайлович']
DOMAINS=['example.ru','mail.ru','company.test','demo.local']
STREETS=['Ленина','Пушкина','Мира','Советская','Гагарина','Садовая']

def luhn(prefix,length=16):
    base=[int(x) for x in prefix]
    while len(base)<length-1: base.append(random.randint(0,9))
    for check in range(10):
        d=base+[check]; s=0; parity=len(d)%2
        for i,x in enumerate(d):
            if i%2==parity:
                x*=2
                if x>9:x-=9
            s+=x
        if s%10==0:return ''.join(map(str,d))

def inn12():
    d=[random.randint(0,9) for _ in range(10)]
    d.append(sum(a*b for a,b in zip(d,[7,2,4,10,3,5,9,4,6,8]))%11%10)
    d.append(sum(a*b for a,b in zip(d,[3,7,2,4,10,3,5,9,4,6,8]))%11%10)
    return ''.join(map(str,d))

def snils():
    while True:
        n=''.join(str(random.randint(0,9)) for _ in range(9))
        s=sum(int(ch)*(9-i) for i,ch in enumerate(n)); c=0 if s<100 or s==101 else s%101
        if c==100:c=0
        return f'{n[:3]}-{n[3:6]}-{n[6:]} {c:02d}'

def add_entity(text,needle,typ,start_from=0):
    s=text.index(needle,start_from); return {'type':typ,'start':s,'end':s+len(needle),'text':needle}

def positive(i):
    fio=f'{random.choice(SURNAMES)} {random.choice(NAMES)} {random.choice(PATR)}'
    dob=f'{random.randint(1,28):02d}.{random.randint(1,12):02d}.{random.randint(1950,2004)}'
    passport=f'паспорт серии {random.randint(1000,9999)} №{random.randint(100000,999999)}'
    email=f'user{i}@{random.choice(DOMAINS)}'
    phone=f'+7 {random.randint(900,999)} {random.randint(100,999)}-{random.randint(10,99)}-{random.randint(10,99)}'
    inn=inn12(); sn=snils(); card=luhn('4')
    address=f'г. Москва, ул. {random.choice(STREETS)}, д. {random.randint(1,150)}, кв. {random.randint(1,300)}'
    templates=[
      (f'Арендатор: {fio}, дата рождения: {dob}, {passport}, email {email}.', [('PERSON',fio),('DATE_OF_BIRTH',dob),('PASSPORT',passport),('EMAIL',email)]),
      (f'Физическое лицо {fio}; телефон: {phone}; ИНН {inn}; СНИЛС {sn}.', [('PERSON',fio),('PHONE',phone),('INN_PERSON','ИНН '+inn),('SNILS','СНИЛС '+sn)]),
      (f'Гражданин {fio}, адрес регистрации: {address}, банковская карта {card}.', [('PERSON',fio),('ADDRESS',address),('BANK_CARD',card)]),
      (f'Представитель: {fio}. Контакты: {email}, {phone}. Дата рождения {dob}.', [('PERSON',fio),('EMAIL',email),('PHONE',phone),('DATE_OF_BIRTH',dob)]),
    ]
    text,pairs=random.choice(templates); ents=[]; cursor=0
    for typ,val in pairs:
        e=add_entity(text,val,typ,cursor); ents.append(e); cursor=e['end']
    return {'id':f'pos_{i:05d}','text':text,'entities':ents,'category':'positive'}

def negative(i):
    org=random.choice(['ООО «Вектор»','АО «Технологии»','ГБУ «Центр закупок»'])
    inn10=random.choice(['7707083893','7710140679'])
    dates=[f'{random.randint(1,28):02d}.{random.randint(1,12):02d}.{random.randint(2025,2029)}' for _ in range(2)]
    templates=[
      f'Настоящий Договор вступает в силу с {dates[0]} и действует до {dates[1]}.',
      f'Арендная плата вносится ежемесячно до 5-го числа. Срок оплаты — {dates[0]}.',
      f'Поставщик: {org}, ИНН {inn10}. Срок поставки до {dates[0]}.',
      f'Протокол составлен {dates[0]}. Заседание назначено на {dates[1]}.',
      f'Стоимость договора составляет {random.randint(100,900)} 000 рублей, включая НДС.',
    ]
    return {'id':f'neg_{i:05d}','text':random.choice(templates),'entities':[],'category':'negative'}

def ambiguous(i):
    d=f'{random.randint(1,28):02d}.{random.randint(1,12):02d}.{random.randint(1950,2029)}'
    return {'id':f'amb_{i:05d}','text':f'Дата: {d}. Документ подписан сторонами.','entities':[], 'category':'ambiguous','expected_review':True}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--rows',type=int,default=2500); ap.add_argument('--seed',type=int,default=42); ap.add_argument('--output',default='data/synthetic/dataset.jsonl'); a=ap.parse_args(); random.seed(a.seed)
    rows=[]
    npos=int(a.rows*.6); nneg=int(a.rows*.35)
    for i in range(npos):rows.append(positive(i))
    for i in range(nneg):rows.append(negative(i))
    for i in range(a.rows-len(rows)):rows.append(ambiguous(i))
    random.shuffle(rows); out=Path(a.output); out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text('\n'.join(json.dumps(x,ensure_ascii=False) for x in rows)+'\n',encoding='utf-8')
    print(json.dumps({'rows':len(rows),'positive':npos,'negative':nneg,'ambiguous':a.rows-npos-nneg,'output':str(out)},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
