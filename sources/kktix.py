"""KKTIX 組織公開活動 — 商業主辦（Spartan 等）。

events.json 的 `published` 是「頁面發布時間」不是賽事日期，不可直接使用。
真實日期在 content 欄位（時間：YYYY/MM/DD HH:MM）與活動頁的 schema.org
JSON-LD（startDate / endDate / offers.availability / offers.validThrough）。

同一場賽事會拆成多個票種（VIP／Normal／Early Bird），需合併為一筆。
"""
import json, re, datetime
from _http import get
import normalize as N
import review as RV

ORGS = {'kwankwan': 'Spartan Race Taiwan（寬寬整合行銷）'}
NAME = 'KKTIX'
TICKET = re.compile(r'^【[^】]*】|\s*[-—]\s*(?:VIP|Normal|Early Bird)\s*$', re.I)

def fetch(enrich_future=True):
    out = {}
    today = datetime.date.today().strftime('%Y%m%d')
    for slug, label in ORGS.items():
        raw = get(f'https://{slug}.kktix.cc/events.json')
        if not raw: continue
        try: entries = json.loads(raw).get('entry', [])
        except Exception as e:
            RV.flag(NAME, slug, f'events.json 解析失敗：{e}'); continue
        for e in entries:
            title = TICKET.sub('', e.get('title', '')).strip()
            if not title: continue
            info = _from_content(e.get('content', ''))
            if not info['date']:
                RV.flag(NAME, title, 'content 沒有可解析的「時間：」欄位',
                        e.get('url', ''), (e.get('content') or '')[:90])
                continue
            key = (title, info['date'])
            if key in out: continue                      # 多票種合併
            ev = N.event(id='kk-%s-%s' % (slug, _base(e['url'])), name=title,
                         date=info['date'], location=info['place'],
                         url=e['url'], source=NAME)
            out[key] = ev
    events = list(out.values())
    if enrich_future:
        for ev in events:
            if ev['d'] >= today: _enrich(ev)
    return events

def _base(url):
    return re.sub(r'-\d+$', '', url.rstrip('/').rsplit('/', 1)[-1])

def _from_content(c):
    """content 形如：時間：2025/10/19 07:00(+0800)~17:30\n地點：新北市鶯歌區…"""
    d, place = '', ''
    m = re.search(r'時間[：:]\s*(\d{4})/(\d{1,2})/(\d{1,2})', c or '')
    if m: d = f'{m.group(1)}{int(m.group(2)):02d}{int(m.group(3)):02d}'
    m = re.search(r'地點[：:]\s*([^\n]{2,50})', c or '')
    if m: place = m.group(1).strip()
    return {'date': d, 'place': place}

def _enrich(ev):
    """未來場次才抓內頁 JSON-LD，取報名截止與售票狀態。"""
    page = get(ev['u'])
    if not page: return
    m = re.search(r'application/ld\+json[^>]*>([\s\S]*?)</script>', page)
    if not m: return
    try: ld = json.loads(m.group(1))
    except Exception: return
    if isinstance(ld, list): ld = ld[0] if ld else {}
    if ld.get('location', {}).get('name') and not ev['l']:
        ev['l'] = ld['location']['name'][:60]
    offers = ld.get('offers') or []
    thru = [o.get('validThrough') for o in offers if o.get('validThrough')]
    if thru: ev['rc'] = min(thru)[:10]
    avail = {(o.get('availability') or '').rsplit('/', 1)[-1] for o in offers}
    if avail and avail <= {'OutOfStock', 'SoldOut'}: ev['st'] = '已額滿'
    elif 'InStock' in avail: ev['st'] = '報名中'
