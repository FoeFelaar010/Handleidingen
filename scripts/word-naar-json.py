"""Zet de Word-handleidingen in word/ om naar public/data/<slug>.json en public/i/*.webp.

Word is de enige bron: pas bij fouten deze omzetter aan, niet de uitvoer.
Overgenomen uit de Lovable-export (scripts/word-naar-site.py); alleen de in- en uitvoer is anders.
Draait in GitHub Actions: python scripts/word-naar-json.py
"""
import re, io, os, glob, shutil, hashlib, html, json, sys, unicodedata, copy
import docx
from docx.text.paragraph import Paragraph
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORD = os.path.join(ROOT, 'word')
OUT_DATA = os.path.join(ROOT, 'public', 'data')
OUT_I = os.path.join(ROOT, 'public', 'i')
CATALOGUS = os.path.join(ROOT, 'src', 'catalogus.json')

KEYS = [('veiligheid','danger'),('veilig werken','danger'),('gevaar','danger'),('dit zijn de regels','danger'),
        ('niet doen','danger'),('alleen met je docent','warn'),('let op','warn'),('check eerst','warn'),
        ('goed om te weten','info'),('tip','tip')]
NB = '\xa0'
# v27-sjabloon: de stijl bepaalt het onderdeel, niet de tekst
BLOK_STIJL = {'Blok Tip':'tip','Blok Let op':'warn','Blok Veilig':'danger','Blok Info':'info'}
BLOK_KLEUR = {'E6F4EA':'tip','FFF3E0':'warn','FBE9E9':'danger','FDECEA':'danger','E8F1F8':'info','D6EBF5':'info'}
KNOP_STIJL = {'Knopnummer':'k-b','KnopnummerGroen':'k-g','KnopnummerOranje':'k-o','KnopnummerRood':'k-r'}
EMU_CM = 360000
e = lambda t: html.escape(t, quote=False)

def slug(t):
    t = unicodedata.normalize('NFKD', t).encode('ascii','ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+','-',t).strip('-') or 'h'

class Conv:
    def __init__(s, path):
        s.d = docx.Document(path); s.imgs = {}
    def img(s, rid):
        if rid in s.imgs: return s.imgs[rid]
        part = s.d.part.related_parts[rid]
        try: im = Image.open(io.BytesIO(part.blob))
        except Exception: s.imgs[rid] = None; return None
        if im.mode not in ('RGB','RGBA'): im = im.convert('RGBA')
        im.thumbnail((1500,1500))
        b = io.BytesIO(); im.save(b,'WEBP',quality=82); data = b.getvalue()
        name = hashlib.md5(data).hexdigest()[:10]+'.webp'
        with open(os.path.join(OUT_I, name),'wb') as f: f.write(data)
        s.imgs[rid] = (name, im.width, im.height); return s.imgs[rid]
    def blips(s, el):
        # Repeated identical drawings inside one paragraph are one illustration.
        # Elk beeld krijgt zijn maat in Word mee (cm): die bepaalt de maat op de site.
        out = {}
        for dr in el.xpath('.//w:drawing'):
            rid = (dr.xpath('.//a:blip/@r:embed') or [None])[0]
            if not rid or rid in out or not s.img(rid): continue
            ext = dr.xpath('.//wp:extent')
            cx, cy = (int(ext[0].get('cx')), int(ext[0].get('cy'))) if ext else (0, 0)
            out[rid] = s.img(rid) + (cx / EMU_CM, cy / EMU_CM)
        return list(out.values())
    def fig(s, info, multi=False, cap=''):
        n,w,h = info[:3]; wcm, hcm = (info[3], info[4]) if len(info) > 3 else (0, 0)
        if wcm:   # v27: breed (>= 10 cm), telefoon (staand), klein
            cls = 'shot' if wcm >= 10 else ('shot tel' if hcm > 1.4 * wcm else 'shot small')
        else:
            cls = 'shot small' if w/h < 1.3 else 'shot'
        c = f'<figcaption>{e(cap)}</figcaption>' if cap else ''
        return (f'<figure class="{cls}"><button aria-label="Vergroot de afbeelding" class="zoom" type="button">'
                f'<img alt="Afbeelding" decoding="async" loading="lazy" src="i/{n}" width="{w}" height="{h}"/></button>{c}</figure>')
    def runs(s, p_el):
        """inline html of a paragraph; knopnummers (nbsp-digit-nbsp) -> blue badge"""
        out = []
        for r in p_el.xpath('./w:r|./w:hyperlink/w:r|./w:ins/w:r|./w:smartTag/w:r'):
            t = ''.join(x.text or '' if x.tag.endswith('}t') else ('\t' if x.tag.endswith('}tab') else (' ' if x.tag.endswith('}br') else ''))
                        for x in r.iter() if x.tag.split('}')[1] in ('t','tab','br'))
            if not t: continue
            rs = r.xpath('./w:rPr/w:rStyle/@w:val')
            if rs and rs[0] in KNOP_STIJL and t.strip(' '+NB):
                out.append(f'<span class="k {KNOP_STIJL[rs[0]]}">{e(t.strip(" "+NB))}</span>'); continue
            m = re.fullmatch(NB+r'(\d{1,2}|AI)'+NB, t)
            if m: out.append(f'<span class="k k-b">{m.group(1)}</span>'); continue
            b = r.xpath('./w:rPr/w:b[not(@w:val="0") and not(@w:val="false")]')
            out.append(f'<b>{e(t)}</b>' if b else e(t))
        return ''.join(out).replace('</b><b>','')
    def ptext(s, p_el):
        return ''.join(x.text or '' for x in p_el.iter() if x.tag.endswith('}t'))
    def style(s, p_el):
        st = Paragraph(p_el, s.d).style; return st.name if st is not None else ""
    # ---- blocks
    def paras_html(s, els):
        """render a list of body/cell children into html"""
        out=[]; i=0; els=list(els)
        while i < len(els):
            el = els[i]; tag = el.tag.split('}')[1]
            if tag == 'tbl': out.append(s.table(el)); i+=1; continue
            if tag != 'p': i+=1; continue
            st = s.style(el); txt = s.ptext(el).strip()
            if st.startswith('toc'): i+=1; continue
            if s.is_step(els[i]):
                items=[]
                while i < len(els) and els[i].tag.endswith('}p') and s.is_step(els[i]):
                    items.append(s.step(els[i])); i+=1
                out.append('<ol class="steps">'+''.join(items)+'</ol>'); continue
            if st == 'Code':
                lines=[]
                while i < len(els) and els[i].tag.endswith('}p') and s.style(els[i])=='Code':
                    lines.append(s.ptext(els[i]).replace(NB,' ')); i+=1
                out.append('<div class="code"><pre>'+e('\n'.join(lines))+'</pre></div>'); continue
            if st in ('List Paragraph','Opsomming') or el.xpath('./w:pPr/w:numPr'):
                items=[]
                while i < len(els) and els[i].tag.endswith('}p') and (s.style(els[i]) in ('List Paragraph','Opsomming') or els[i].xpath('./w:pPr/w:numPr')):
                    if s.ptext(els[i]).strip(): items.append('<li>'+s.runs(els[i])+'</li>')
                    i+=1
                out.append('<ul>'+''.join(items)+'</ul>'); continue
            bl = s.blips(el)
            if bl:
                cap=''
                if i+1<len(els) and els[i+1].tag.endswith('}p') and s.style(els[i+1])=='Bijschrift PORT':
                    cap=s.ptext(els[i+1]).strip(); i+=1
                if len(bl) > 1:   # kleine afbeeldingen naast elkaar in één alinea
                    out.append('<div class="mt-row">'+''.join(s.fig(b) for b in bl)+'</div>'+(f'<p class="cap"><i>{e(cap)}</i></p>' if cap else ''))
                else:
                    out.append(s.fig(bl[0], cap=cap))
                if txt: out.append('<p>'+s.runs(el)+'</p>')
                i+=1; continue
            if not txt: i+=1; continue
            if st == 'Heading 2': out.append(f'<h3>{e(txt)}</h3>')
            elif st == 'Bijschrift PORT': out.append(f'<p class="cap"><i>{e(txt)}</i></p>')
            else: out.append('<p>'+s.runs(el)+'</p>')
            i+=1
        return ''.join(out)
    def is_step(s, el):
        if not el.tag.endswith('}p'): return False
        if s.style(el) == 'Stap': return True
        if el.xpath('./w:r[1]/w:rPr/w:rStyle[@w:val="Stapletter"]'): return True
        return bool(re.match('^'+NB+r'?[A-Z]'+NB+r'?\t', s.ptext(el)))
    def step(s, el):
        first = el.xpath('./w:r[w:t][1]')
        if first and first[0].xpath('./w:rPr/w:rStyle[@w:val="Stapletter"]'):
            letter = s.ptext(first[0]).strip(' '+NB)
            rest = copy.deepcopy(el)
            for r in rest.xpath('./w:r'):
                if r.xpath('./w:rPr/w:rStyle[@w:val="Stapletter"]') or (not s.ptext(r).strip() and r.xpath('./w:tab')): rest.remove(r)
                else: break
            return f'<li><span class="badge">{e(letter)}</span><div class="st">{s.runs(rest).strip()}</div></li>'
        h = s.runs(el)
        m = re.match(r'^\s*(?:'+NB+r')?\s*([A-Z])\s*(?:'+NB+r')?\s*\t?', html.unescape(re.sub('<[^>]+>','',h)))
        letter = m.group(1) if m else ''
        h = re.sub(r'^(<b>)?\s*'+NB+'?'+letter+NB+r'?\s*\t?', r'\1', h, count=1) if letter else h
        h = h.replace('<b></b>','').strip()
        return f'<li><span class="badge">{letter}</span><div class="st">{h}</div></li>'
    def cell_children(s, tc): return list(tc.iterchildren())
    def table(s, tbl):
        rows = tbl.xpath('./w:tr')
        grid = [[tc for tc in tr.xpath('./w:tc')] for tr in rows]
        ncell = sum(len(r) for r in grid)
        # 1 cell
        if ncell == 1:
            tc = grid[0][0]; kids = s.cell_children(tc)
            ps = [k for k in kids if k.tag.endswith('}p') and s.ptext(k).strip()]
            bl = s.blips(tc)
            caps = [s.ptext(p).strip() for p in ps]
            # fotokader: alleen beelden (+ evt. onderschrift "Foto: ...") -> neutraal kader, beelden naast elkaar
            if bl and all(c.lower().startswith('foto:') for c in caps):
                figs = ''.join(s.fig(b) for b in bl)
                cap = ''.join(f'<p class="cap"><i>{e(c)}</i></p>' for c in caps)
                return f'<div class="pics"><div class="mt-row">{figs}</div>{cap}</div>'
            if not ps: return s.paras_html(kids)
            first = caps[0]; low = first.lower()
            if re.match(r'(screenshot|foto) volgt', low):
                return f'<aside class="blk ph"><p>📷 {e(first)}</p></aside>'
            kind = (BLOK_STIJL.get(s.style(ps[0]))
                    or BLOK_KLEUR.get((tc.xpath('./w:tcPr/w:shd/@w:fill') or [''])[0].upper())
                    or next((c for k,c in KEYS if low.startswith(k)), 'info'))
            body = [k for k in kids if k is not ps[0]]
            return f'<aside class="blk {kind}"><p class="blk-t">{e(first)}</p>{s.paras_html(body)}</aside>'
        # phases: one row with arrows
        if len(grid)==1 and (any(s.ptext(tc).strip() in ('→','➜','>') for tc in grid[0]) or (len(grid[0])>=3 and all(re.match(r'\d+\.',s.ptext(tc).strip()) for tc in grid[0]))):
            lis=[]
            for tc in grid[0]:
                ps=[s.ptext(p).strip() for p in tc.xpath('./w:p') if s.ptext(p).strip()]
                if not ps or ps[0] in ('→','➜','>'): continue
                m = re.match(r'(\d+)\.\s*(.*)', ps[0])
                n,t = (m.group(1),m.group(2)) if m else ('',ps[0])
                lis.append(f'<li><span class="pn">{n}</span><span><b>{e(t)}</b><small>{e(" ".join(ps[1:]))}</small></span></li>')
            return '<ol class="phases">'+''.join(lis)+'</ol>'
        # v27 'Naast elkaar' met nog een lege plek: tekst links, grijs vak rechts
        if len(grid)==1 and len(grid[0])==2 and not tbl.xpath('.//a:blip'):
            ph = [tc for tc in grid[0] if re.match(r'(screenshot|foto) volgt', s.ptext(tc).strip().lower())]
            if len(ph)==1:
                t = [tc for tc in grid[0] if tc is not ph[0]][0]
                return (f'<div class="mt"><div class="mt-t">{s.paras_html(s.cell_children(t))}</div>'
                        f'<div class="mt-m"><aside class="blk ph"><p>📷 {e(s.ptext(ph[0]).strip())}</p></aside></div></div>')
        has_img = bool(tbl.xpath('.//a:blip'))
        # vergelijkingstabel: foto's alleen in de kopregel, daaronder tekstrijen -> echte tabel
        matrix = has_img and len(grid)>2 and len(grid[0])>=3 and not any(tc.xpath('.//a:blip') for r in grid[1:] for tc in r)
        if has_img and not matrix:
            out=[]
            for r in grid:
                imgc = [tc for tc in r if tc.xpath('.//a:blip')]
                txtc = [tc for tc in r if s.ptext(tc).strip() and tc not in imgc]
                mixed_txt = [tc for tc in imgc if s.ptext(tc).strip()]
                media = ''.join(s.paras_html(s.cell_children(tc)) if tc in mixed_txt else ''.join(s.fig(b) for b in s.blips(tc)) for tc in imgc)
                text = ''.join(s.paras_html(s.cell_children(tc)) for tc in txtc)
                if text and media: out.append(f'<div class="mt"><div class="mt-t">{text}</div><div class="mt-m">{media}</div></div>')
                elif media: out.append(f'<div class="mt-row">{media}</div>' if len(imgc)>1 else media)
                elif text: out.append(text)
            return ''.join(out)
        # data table
        head = grid[0]; hb = matrix or (all(tc.xpath('.//w:b') or not s.ptext(tc).strip() for tc in head) and len(grid)>1)
        def cell(tc, th=False):
            ps=[k for k in s.cell_children(tc) if k.tag.endswith('}p') or k.tag.endswith('}tbl')]
            inner = '<br>'.join(s.runs(p) for p in ps if p.tag.endswith('}p') and s.ptext(p).strip())
            if any(p.tag.endswith('}tbl') for p in ps): inner = s.paras_html(ps)
            im = ''.join(f'<img class="ti" alt="" loading="lazy" src="i/{b[0]}" width="{b[1]}" height="{b[2]}"/>' for b in s.blips(tc))
            inner = im + inner
            gs = tc.xpath('./w:tcPr/w:gridSpan/@w:val'); cs = f' colspan="{gs[0]}"' if gs and gs[0]!='1' else ''
            return f'<th scope="col"{cs}>{inner}</th>' if th else f'<td{cs}>{inner}</td>'
        h = '<div class="tw"><table class="cmp">' if matrix else '<div class="tw"><table class="stack">'
        if hb: h += '<thead><tr>'+''.join(cell(tc,True) for tc in head)+'</tr></thead>'
        h += '<tbody>'+''.join('<tr>'+''.join(cell(tc) for tc in r)+'</tr>' for r in (grid[1:] if hb else grid))+'</tbody></table></div>'
        return h
    def convert(s):
        body = [el for el in s.d.element.body.iterchildren() if el.tag.split('}')[1] in ('p','tbl')]
        # title = first table
        t0 = body[0]; title=sub=''
        if t0.tag.endswith('}tbl'):
            ps=[s.ptext(p).strip() for p in t0.xpath('.//w:p') if s.ptext(p).strip()]
            title = ps[0] if ps else ''; sub = '<br>'.join(e(x) for x in ps[1:]); body = body[1:]
        intro=[]; secs=[]; cur=None
        for el in body:
            if el.tag.endswith('}p') and s.style(el)=='Heading 1' and s.ptext(el).strip():
                if s.ptext(el).strip().lower().startswith('bouwstenen'): break   # sjabloonpagina: niet op de site
                cur=[s.ptext(el).strip(),[]]; secs.append(cur); continue
            if el.tag.endswith('}p') and s.style(el)=='Heading 2' and s.ptext(el).strip().lower().startswith('inhoud') and cur is None: continue
            (cur[1] if cur else intro).append(el)
        out_secs=[]; used=set()
        for t,els in secs:
            sl=slug(t)
            while sl in used: sl+='-2'
            used.add(sl); out_secs.append((sl,t,s.paras_html(els)))
        return title, sub, s.paras_html(intro), out_secs

def wordtexts(path):
    d=docx.Document(path); out=[]; stop=[False]
    def walk(el):
        for k in el.iterchildren():
            if stop[0]: return
            t=k.tag.split('}')[1]
            if t=='p':
                st=getattr(Paragraph(k,d).style,"name","") or ""
                if st.startswith('toc'): continue
                x=''.join(z.text or '' for z in k.iter() if z.tag.endswith('}t'))
                if st=='Heading 1' and x.strip().lower().startswith('bouwstenen'): stop[0]=True; return
                if x.strip(): out.append(x)
            elif t=='tbl':
                for tc in k.xpath('.//w:tc'):
                    if not tc.xpath('ancestor::w:tc'): walk(tc)
    walk(d.element.body); return out
def norm(t): return re.sub(r'[\s\xa0]+','',html.unescape(t)).lower()

def nieuwste(bron):
    """Nieuwste versie van een Word-bestand: Handleiding_Teams_v26_02.docx wint van _v26_01 en _v0_4."""
    best = None
    for p in glob.glob(os.path.join(ROOT, '**', glob.escape(bron) + '_v*.docx'), recursive=True):
        m = re.search(r'_v(\d+)_(\d+)\.docx$', p)
        if not m or os.path.basename(p).startswith('~$'): continue
        key = (int(m.group(1)), int(m.group(2)))
        if best is None or key > best[0]: best = (key, p, f'{int(m.group(1))}.{m.group(2)}')
    return best

if __name__=='__main__':
    for d in (OUT_DATA, OUT_I):
        shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
    items = [it for g in json.load(open(CATALOGUS, encoding='utf-8'))['groepen'] for it in g['items']]
    fouten = 0
    for it in items:
        gevonden = nieuwste(it['bron'])
        if not gevonden:
            print(f"::warning::Geen Word-bestand voor {it['slug']} (verwacht word/{it['bron']}_vX_Y.docx)")
            continue
        _, pad, versie = gevonden
        try:
            c = Conv(pad); title, sub, intro, secs = c.convert()
        except Exception as ex:
            fouten += 1
            print(f"::error::{os.path.basename(pad)} kon niet worden omgezet: {ex!r}")
            continue
        alles = norm(re.sub(r'<[^>]+>','', title + sub + intro + ''.join(h for _,_,h in secs) + ''.join(t for _,t,_ in secs)))
        mis = [w for w in wordtexts(pad) if norm(w).strip('→➜>') and norm(w)!='inhoud' and re.sub(r'^\d+\.','',norm(w)) not in alles]
        data = {'slug': it['slug'], 'titel': title, 'sub': sub, 'intro': intro, 'versie': versie,
                'bron': os.path.basename(pad), 'secties': [{'id': sl, 'titel': t, 'html': h} for sl,t,h in secs]}
        with open(os.path.join(OUT_DATA, it['slug'] + '.json'), 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
        print(f"{it['slug']}: {os.path.basename(pad)} · {len(secs)} hoofdstukken · {len(c.imgs)} afbeeldingen · {len(mis)} alinea's niet gevonden")
        for w in mis[:5]:
            print(f"::warning::{it['slug']}: alinea staat niet op de site: {w[:80]}")
    sys.exit(1 if fouten else 0)
