import sys, os, re, json
from bs4 import BeautifulSoup
d = sys.argv[1]; out=[]
for fn in sorted(os.listdir(d)):
    s = open(os.path.join(d,fn), encoding='utf-8', errors='ignore').read()
    soup = BeautifulSoup(s, 'lxml')
    g = lambda sel, attr='content': (soup.select_one(sel) or {}).get(attr) if soup.select_one(sel) else None
    canon = g('link[rel=canonical]','href')
    ld = {}
    for sc in soup.select('script[type="application/ld+json"]'):
        try:
            j=json.loads(sc.string)
            for n in j.get('@graph',[j]):
                if n.get('@type') in ('BlogPosting','Article','NewsArticle'): ld=n
        except Exception: pass
    types = sorted(set(re.findall(r'"@type":"([A-Za-z]+)"', s)))
    c = soup.select_one('.content-inner') or soup.select_one('.post-content')
    if not c: continue
    for bad in c.select('script,style'): bad.decompose()
    text = c.get_text(' ', strip=True)
    heads = [(h.name, h.get_text(' ',strip=True)) for h in c.select('h1,h2,h3,h4')]
    paras = [p.get_text(' ',strip=True) for p in c.select('p') if p.get_text(strip=True)]
    links = [a.get('href','') for a in c.select('a[href]')]
    internal = [l for l in links if '21degrees.in' in l or l.startswith('/')]
    external = [l for l in links if l.startswith('http') and '21degrees.in' not in l]
    imgs = c.select('img')
    cats = [a.get_text(strip=True) for a in soup.select('a[rel~=tag], .meta-category a')]
    out.append(dict(
        file=fn, url=canon,
        title=(soup.title.string or '').strip() if soup.title else '',
        h1=[h.get_text(' ',strip=True) for h in soup.select('h1')],
        meta_desc=g('meta[name=description]'),
        og_title=g('meta[property="og:title"]'),
        robots=g('meta[name=robots]'),
        published=ld.get('datePublished'), modified=ld.get('dateModified'),
        author=(ld.get('author') or {}).get('name'),
        keywords=ld.get('keywords'), section=ld.get('articleSection'),
        schema_types=types, categories=sorted(set(cats)),
        words=len(text.split()), n_paras=len(paras),
        avg_para_words=round(sum(len(p.split()) for p in paras)/max(1,len(paras)),1),
        headings=heads, n_h2=sum(1 for h in heads if h[0]=='h2'), n_h3=sum(1 for h in heads if h[0]=='h3'),
        n_lists=len(c.select('ul,ol')), n_li=len(c.select('li')), n_tables=len(c.select('table')),
        n_bold=len(c.select('strong,b')), n_imgs=len(imgs), img_alts=[i.get('alt','') for i in imgs],
        internal_links=internal, external_links=external,
        has_faq=bool(re.search(r'\bFAQ|Frequently Asked', text, re.I)),
        questions_in_heads=sum(1 for h in heads if h[1].strip().endswith('?')),
        first_para=paras[0] if paras else '', last_paras=paras[-3:],
        text=text))
json.dump(out, open(sys.argv[2],'w'), indent=1, ensure_ascii=False)
print(len(out))
