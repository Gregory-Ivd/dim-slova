import re
BOOKS={'Иоанна':'JHN','Матфея':'MAT','Марка':'MRK','Луки':'LUK','Деяния':'ACT','Римлянам':'ROM','1-е Коринфянам':'1CO','2-е Коринфянам':'2CO','Галатам':'GAL','Ефесянам':'EPH','Филиппийцам':'PHP','Колоссянам':'COL','2-е Тимофею':'2TI','Евреям':'HEB','Иакова':'JAS','1-е Петра':'1PE','2-е Петра':'2PE','1-е Иоанна':'1JN','Откровения':'REV','Откровение':'REV','1-я Царств':'1SA','2-я Царств':'2SA','3-я Царств':'1KI','4-я Царств':'2KI','Амос':'AMO','Притчи':'PRO','Иезекииль':'EZK','Иеремия':'JER','Псалом':'PSA','Даниил':'DAN','Числа':'NUM','Исаия':'ISA','Иисус Навин':'JOS','Второзаконие':'DEU','Иов':'JOB','Осия':'HOS','Малахия':'MAL','Бытие':'GEN',
 'Матф.':'MAT','Mатф.':'MAT','Ис.':'ISA','Втор.':'DEU','Пс.':'PSA','Быт.':'GEN','Луки.':'LUK','Лк.':'LUK'}
UA={'JHN':'Івана','MAT':'Матвія','MRK':'Марка','LUK':'Луки','ACT':'Дії','ROM':'Римлян','1CO':'1 Коринтян','2CO':'2 Коринтян','GAL':'Галатів','EPH':'Ефесян','PHP':'Филип’ян','COL':'Колосян','2TI':'2 Тимофія','HEB':'Євреїв','JAS':'Якова','1PE':'1 Петра','2PE':'2 Петра','1JN':'1 Івана','REV':'Об’явлення','1SA':'1 Самуїла','2SA':'2 Самуїла','1KI':'1 Царів','2KI':'2 Царів','AMO':'Амос','PRO':'Приповісті','EZK':'Єзекиїль','JER':'Єремія','PSA':'Псалом','DAN':'Даниїл','NUM':'Числа','ISA':'Ісая','JOS':'Ісус Навин','DEU':'Повторення Закону','JOB':'Іов','HOS':'Осія','MAL':'Малахія','GEN':'Буття'}
# Synodal -> CUV (Hebrew) verse shifts
def remap(book,ch,v):
    if book=='PSA' and ch==118: return 119,v
    if book=='PSA' and ch==90: return 91,v
    if book=='DAN' and ch==6: return 6,v+1
    if book=='JOS' and ch==6 and v==25: return 6,26
    return ch,v
def parse(ref):
    ref=ref.strip().replace('\u00a0',' ')
    m=re.match(r'^(.*?)\s*(\d+):\s*([\d,\-–\s]+)$',ref)
    name,ch,vs=m.group(1).strip(),int(m.group(2)),m.group(3).replace(' ','').replace('–','-')
    book=BOOKS[name]
    out=[]
    for part in vs.split(','):
        if not part: continue
        if '-' in part: a,b=map(int,part.split('-'))
        else: a=b=int(part)
        out.append((a,b))
    return book,ch,out
