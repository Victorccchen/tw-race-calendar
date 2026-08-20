"""個人商戶／小型專業主辦（野托邦、X-Camp 等）。

這類主辦的活動有獨特性 —— 常態開課、小班、含裝備與教學，涵蓋登山車、
登山、衝浪、越野跑、潛水等。但官網多為 SPA 或社群頁，無法穩定自動解析。

流程（依「初期人工驗證、穩定後自動化」）：
  1. 自動偵測每個主辦頁面的內容指紋，有變動即進待驗證佇列
  2. 人工確認後把場次寫進 data/indie_operators.json 的 events
  3. 只有寫進 events（且有 verified 日期）的才會出現在前台
"""
import json, os, re, hashlib, html
from _http import get
import normalize as N
import review as RV

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONF = os.path.join(ROOT, 'data', 'indie_operators.json')
FING = os.path.join(ROOT, 'data', 'indie_fingerprints.json')
NAME = '個人商戶'

def fetch(watch=True):
    conf = json.load(open(CONF, encoding='utf-8'))
    out = []
    for op in conf['operators']:
        for it in op.get('events', []):
            if not it.get('verified'):
                RV.flag(op['name'], it.get('name', '(未命名)'),
                        '尚未人工驗證，未進前台', it.get('url', ''))
                continue
            e = N.event(
                id=it['id'], name=it['name'], date=it['date'],
                city=it.get('city') or op.get('city', ''), location=it.get('location', ''),
                groups=it.get('groups', []), sport=it.get('sport') or op.get('sport'),
                kind=it.get('kind'), kid=it.get('kid'),
                age=it.get('age', ''), fee=it.get('fee', ''),
                url=it.get('url') or op['url'], source=op['name'])
            e['o'] = 'indie'                       # 個人商戶標記
            if it.get('recurring'): e['r'] = 1     # 常態開課
            out.append(e)
    if watch: _watch(conf)
    return out

def _watch(conf):
    """偵測主辦頁面變動 —— 有變動代表可能有新梯次，需人工看一眼。"""
    old = json.load(open(FING, encoding='utf-8')) if os.path.exists(FING) else {}
    new = {}
    for op in conf['operators']:
        if not op.get('watch'): continue
        page = get(op['url'])
        if not page:
            RV.flag(op['name'], op['name'], '官網取得失敗，無法確認是否有新梯次', op['url'])
            continue
        txt = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', html.unescape(page)))
        fp = hashlib.sha256(txt.encode()).hexdigest()[:16]
        new[op['id']] = fp
        if op['id'] in old and old[op['id']] != fp:
            RV.flag(op['name'], op['name'], '官網內容有變動，請確認是否新增梯次或改期', op['url'])
    json.dump(new, open(FING, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
