import re as _re
def clean(t):
    t=_re.sub(r'\s+',' ',t)
    t=_re.sub(r'([(\[])\s+',r'\1',t)
    t=_re.sub(r'\s+([,.;:!?)\]])',r'\1',t)
    return t.strip()
import re,sys,os,urllib.request,time
from html.parser import HTMLParser
D=os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','.cache')
class P(HTMLParser):
    def __init__(s):
        super().__init__(); s.stack=[]; s.v={}; s.heads=[]; s.cur=None
    def handle_starttag(s,tag,a):
        a=dict(a); cls=a.get('class','') or ''
        info={'tag':tag,'verse':None,'note':'__note' in cls,'content':'__content' in cls,'head':'__heading' in cls,'label':'__label' in cls}
        if '__verse' in cls and a.get('data-usfm'):
            info['verse']=a['data-usfm']
        s.stack.append(info)
        s.newspan=True
    def handle_endtag(s,tag):
        while s.stack:
            x=s.stack.pop()
            if x['tag']==tag: break
    def handle_data(s,d):
        if any(x['note'] for x in s.stack): return
        if any(x['head'] for x in s.stack): s.heads.append(d); return
        vv=[x['verse'] for x in s.stack if x['verse']]
        if vv and any(x['content'] for x in s.stack):
            for u in vv[-1].split('+'):
                pass
            u=vv[-1].split('+')[0]
            s.v[u]=s.v.get(u,'')+(' ' if getattr(s,'newspan',False) else '')+d
            s.newspan=False
def chapter(book,ch):
    fn=os.path.join(D,f'{book}.{ch}.html')
    if not os.path.exists(fn):
        req=urllib.request.Request(f'https://www.bible.com/bible/3786/{book}.{ch}.CUV',headers={'User-Agent':'Mozilla/5.0'})
        open(fn,'w',encoding='utf-8').write(urllib.request.urlopen(req).read().decode('utf-8')); time.sleep(0.4)
    h=open(fn,encoding='utf-8').read()
    p=P(); p.feed(h)
    out={}
    for u,t in p.v.items():
        b,c,v=u.split('.')
        if b==book and int(c)==int(ch): out[int(v)]=clean(t)
    return out,p.heads
if __name__=='__main__':
    b,c=sys.argv[1],sys.argv[2]
    vs,hd=chapter(b,c)
    for v in sys.argv[3:]: print(v,vs.get(int(v)))
