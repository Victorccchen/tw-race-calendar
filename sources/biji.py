"""運動筆記 — 路跑／越野／鐵人主來源，欄位最完整（含報名開窗）。"""
import re, html
from urllib.parse import unquote
from _http import get
import normalize as N

URL = 'https://running.biji.co/index.php?q=competition'
NAME = '運動筆記'

def fetch():
    raw = get(URL)
    if not raw: return []
    raw = re.sub(r'<!--.*?-->', '', raw, flags=re.S)
    parts = re.split(r"<div id='cp_part_(\d+)' class=\"competition-list-row\"", raw)[1:]
    out = []
    for cid, block in zip(parts[0::2], parts[1::2]):
        cal = re.search(r'text=([^&]*)&dates=(\d{8})/(\d{8})&location=([^&]*)&details=(.*?)"',
                        block, re.S)
        if not cal: continue
        name = html.unescape(unquote(cal.group(1)))
        loc  = html.unescape(unquote(cal.group(4)))
        det  = html.unescape(unquote(cal.group(5)))
        r = re.search(r'報名日期:([\d\-: ]+)~([\d\-: ]+)', det)
        ro, rc = (r.group(1).strip(), r.group(2).strip()) if r else ('', '')
        groups = [g.strip() for g in
                  re.findall(r'<div class="event-item event_item">\s*([^<]+?)\s*</div>', block)]
        st = re.search(r'<div class="competition-status">(.*?)</div>', block, re.S)
        st = html.unescape(re.sub(r'<[^>]+>', ' ', st.group(1))).strip() if st else ''
        col = re.search(r'class="collect_count">\s*([\d,]+)', block)
        ev = N.event(
            id='biji-'+cid, name=name, date=cal.group(2), location=loc, groups=groups,
            reg_open=ro, reg_close=rc, status=st, source=NAME,
            url=f'https://running.biji.co/index.php?q=competition&act=info&cid={cid}')
        if col: ev['p'] = int(col.group(1).replace(',', ''))   # 收藏數 ≈ 賽事規模
        out.append(ev)
    return out
