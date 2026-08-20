"""日月潭國家風景區管理處 — 萬人泳渡、L'Étape 環法、Come!BikeDay 等。

頁面為靜態 HTML，活動卡片結構穩定：
  <a href="...id=N" title="..." class="seasonintro-card">
    <div class="card-title">名稱</div><div class="card-date">YYYY-MM-DD ~ YYYY-MM-DD</div>
以 id 作為穩定識別碼（不可用 hash(name)，會因 PYTHONHASHSEED 每次改變）。
"""
import re, html
from _http import get
import normalize as N

URL  = 'https://www.sunmoonlake.gov.tw/events/Activitys?a=24'
NAME = '日月潭風管處'
# 只收運動類，過濾掉音樂會／花火／櫻花季等純觀光活動
SPORTY = re.compile(r'泳渡|路跑|馬拉松|自行車|單車|BikeDay|Étape|Etape|鐵人|健行|登山|挑戰賽')

def fetch():
    raw = get(URL)
    if not raw: return []
    out = {}
    for m in re.finditer(
            r'<a[^>]+href="[^"]*id=(\d+)"[^>]*class="seasonintro-card"[\s\S]{0,900}?'
            r'<div class="card-title">\s*([^<]+?)\s*</div>[\s\S]{0,200}?'
            r'<div class="card-date">\s*(\d{4})-(\d{2})-(\d{2})', raw):
        aid, name = m.group(1), html.unescape(m.group(2)).strip()
        if not SPORTY.search(name): continue
        out[aid] = N.event(
            id='smn-' + aid, name=name,
            date=f'{m.group(3)}{m.group(4)}{m.group(5)}',
            city='南投', location='南投縣魚池鄉 日月潭',
            url=f'https://www.sunmoonlake.gov.tw/Events/Activitys?a=24&id={aid}',
            source=NAME)
    return list(out.values())
