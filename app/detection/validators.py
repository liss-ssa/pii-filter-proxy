import re

def luhn_ok(value: str) -> bool:
    digits=[int(x) for x in re.sub(r"\D", "", value)]
    if len(digits) not in range(13,20): return False
    checksum=0; parity=len(digits)%2
    for i,d in enumerate(digits):
        if i%2==parity:
            d*=2
            if d>9:d-=9
        checksum+=d
    return checksum%10==0

def inn_ok(value: str) -> bool:
    d=[int(x) for x in re.sub(r"\D", "", value)]
    if len(d)==10:
        return sum(a*b for a,b in zip(d[:9],[2,4,10,3,5,9,4,6,8]))%11%10==d[9]
    if len(d)==12:
        c11=sum(a*b for a,b in zip(d[:10],[7,2,4,10,3,5,9,4,6,8]))%11%10
        c12=sum(a*b for a,b in zip(d[:11],[3,7,2,4,10,3,5,9,4,6,8]))%11%10
        return c11==d[10] and c12==d[11]
    return False

def snils_ok(value: str) -> bool:
    d=re.sub(r"\D", "", value)
    if len(d)!=11:return False
    n=d[:9]; control=int(d[9:])
    s=sum(int(ch)*(9-i) for i,ch in enumerate(n))
    expected=0 if s<100 or s==101 else s%101
    if expected==100: expected=0
    return expected==control
