"""比對前後兩份快照，產出異動清單。自動偵測、人工放行——不直接改前台。"""
FIELDS = {'d':'日期','rc':'報名截止','ro':'報名開始','st':'報名狀態',
          'l':'地點','g':'組別','u':'報名連結','n':'名稱','a':'年齡限制','f':'費用'}
SEV = {'改期':'high','連結失效':'high','報名狀態':'high','報名截止':'med','報名開始':'med',
       '新增':'med','消失':'med','組別':'low','地點':'low','名稱':'low','年齡限制':'low','費用':'low'}

def compare(old, new, dead_links=(), today=''):
    o = {e['i']: e for e in old}
    n = {e['i']: e for e in new}
    ch = []
    for i in n.keys() - o.keys():
        e = n[i]
        ch.append(dict(kind='新增', id=i, name=e['n'], date=e['d'], src=e['src'],
                       detail=f"{e['c']} · {LBL(e)}", url=e['u']))
    for i in o.keys() - n.keys():
        e = o[i]
        if today and e['d'] < today:
            continue                      # 賽期已過，自然退場，不算異動
        ch.append(dict(kind='消失', id=i, name=e['n'], date=e['d'], src=e['src'],
                       detail='來源已不再列出，可能已改期、額滿或下架', url=e['u']))
    for i in o.keys() & n.keys():
        a, b = o[i], n[i]
        for f, label in FIELDS.items():
            va, vb = a.get(f), b.get(f)
            if va == vb: continue
            kind = '改期' if f == 'd' else label
            ch.append(dict(kind=kind, id=i, name=b['n'], date=b['d'], src=b['src'],
                           detail=f"{label}：{_s(va)} → {_s(vb)}", url=b['u']))
    for i, reason in dead_links:
        e = n.get(i)
        if e: ch.append(dict(kind='連結失效', id=i, name=e['n'], date=e['d'], src=e['src'],
                             detail=reason, url=e['u']))
    ch.sort(key=lambda c: ({'high':0,'med':1,'low':2}[SEV.get(c['kind'],'low')], c['date']))
    return ch

def LBL(e): return e.get('s','')
def _s(v):
    if isinstance(v, list): return '/'.join(v) or '（空）'
    return str(v) if v not in (None, '') else '（空）'

def to_markdown(ch, date, totals):
    hi = [c for c in ch if SEV.get(c['kind']) == 'high']
    md = [f"# 賽事異動清單 · {date}", "",
          f"資料庫共 **{totals['total']}** 場；今日異動 **{len(ch)}** 筆"
          f"（需確認 {len(hi)} 筆）。", ""]
    if not ch:
        md += ["今日沒有偵測到異動。", ""]
        return '\n'.join(md)
    for sev, title in [('high','## 需要確認'), ('med','## 一般異動'), ('low','## 細節變更')]:
        rows = [c for c in ch if SEV.get(c['kind'],'low') == sev]
        if not rows: continue
        md += [title, "", "| 類型 | 賽事 | 日期 | 異動內容 | 來源 |", "|---|---|---|---|---|"]
        for c in rows:
            d = c['date']
            d = f"{d[:4]}-{d[4:6]}-{d[6:]}" if len(d) == 8 else d
            name = f"[{c['name'][:34]}]({c['url']})" if c['url'] else c['name'][:34]
            md.append(f"| {c['kind']} | {name} | {d} | {c['detail'][:70]} | {c['src']} |")
        md.append("")
    return '\n'.join(md)
