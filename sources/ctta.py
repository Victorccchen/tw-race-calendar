"""中華民國網球協會 — 網球賽事權威來源。

列表頁只有標題與公告日，日期不可靠（標題的 [MMDD-MMDD] 沒有年份）。
因此逐一抓取賽事內頁，從「比賽日期／比賽時間」欄位取真實日期。
解析不出可信日期者不收，改列入待驗證佇列。
"""
import re, html, time
from _http import get
import normalize as N
import dates as DT
import review as RV

BASE  = 'https://www.tennis.org.tw/web/event_information.asp'
CATS  = {1:'全國排名賽', 2:'青少年排名賽', 3:'壯年排名賽', 4:'乙組排名賽',
         5:'學校暨社會團體組賽事', 6:'綜合性賽事', 7:'國際青少年',
         8:'國際男女職業賽', 9:'大專及其他賽事'}
NAME  = '中華民國網球協會'
DATE_KW = ['比賽日期', '比賽時間', '賽事日期', '活動日期', '競賽日期']
REG_KW  = ['報名日期', '報名時間', '報名期限', '截止報名', '報名截止']
PLACE_KW = ['比賽場地', '比賽地點', '賽事地點', '競賽地點']

def _text(h):
    t = html.unescape(re.sub(r'<script[\s\S]*?</script>|<style[\s\S]*?</style>', '', h))
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', t))

def fetch(max_detail=110, delay=0.35):
    seen, out, n = {}, [], 0
    for s in CATS:
        raw = get(f'{BASE}?s={s}')
        if not raw: continue
        body = raw[raw.find('Search...'):]
        for mid, title in re.findall(r'<a[^>]*msg_id=(\d+)[^>]*>\s*(.*?)\s*</a>', body):
            title = html.unescape(re.sub(r'<[^>]+>', '', title)).strip()
            if not title or mid in seen: continue
            seen[mid] = (s, title)
    for mid, (s, title) in list(seen.items())[:max_detail]:
        url = f'{BASE}?s={s}&msg_id={mid}'
        page = get(url)
        n += 1
        time.sleep(delay)
        if not page:
            RV.flag(NAME, title, '內頁取得失敗', url); continue
        txt = _text(page)
        d = DT.first_after(txt, DATE_KW)
        if not d:
            d = DT.cross_checked(txt)          # 次要規則，需兩訊號一致
            if d: RV.flag(NAME, title, f'以次要規則解析出 {d}（西元日期與賽程區間一致），建議抽查', url)
        if not d:
            RV.flag(NAME, title, '整筆未收：內頁找不到可解析的比賽日期', url,
                    _snippet(txt, DATE_KW)); continue
        rc = DT.first_after(txt, REG_KW) or ''
        if rc and not DT.plausible_reg(rc, d):
            RV.flag(NAME, title, f'僅捨棄報名截止 {rc}（疑為年齡分級出生日），賽事本身已收錄', url)
            rc = ''
        out.append(N.event(id=f'ctta-{mid}', name=title, date=d,
                           location=_place(txt), sport='tennis',
                           reg_close=f'{rc[:4]}-{rc[4:6]}-{rc[6:]}' if rc else '',
                           url=url, source=NAME))
    return out

def _snippet(t, kws):
    for kw in kws:
        i = t.find(kw)
        if i >= 0: return t[i:i+90]
    return ''

def _place(t):
    for kw in PLACE_KW:
        m = re.search(kw + r'\s*[:：]?\s*([^\s。，(（]{3,28})', t)
        if m: return m.group(1)
    return ''
