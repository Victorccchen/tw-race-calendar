"""Google Places：依浪點座標搜尋高評價衝浪店家。

Google Maps 的評分無法從網頁取得（爬 Maps 違反其服務條款），必須走官方
Places API。因此本模組需要環境變數 GOOGLE_MAPS_API_KEY；未設定時整個
來源會安靜略過，不影響其他來源。

只收評分達門檻、且評論數足夠的店家 —— 五顆星但只有 3 則評論不算高評價。
API 只提供店家層級資訊（名稱、地址、評分、電話、官網），不含課程與價目，
因此撈到的店家一律進待驗證佇列，由人工補上服務內容後才進前台。
"""
import os, json, urllib.parse
from _http import get
import review as RV

NAME = 'Google Places'
ENDPOINT = 'https://maps.googleapis.com/maps/api/place'
MIN_RATING = float(os.environ.get('PLACES_MIN_RATING', '4.8'))
MIN_REVIEWS = int(os.environ.get('PLACES_MIN_REVIEWS', '20'))
RADIUS = 3000

def fetch():
    key = os.environ.get('GOOGLE_MAPS_API_KEY')
    if not key:
        print('  （未設定 GOOGLE_MAPS_API_KEY，略過 Places 搜尋）')
        return []
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    spots = json.load(open(os.path.join(root, 'data', 'surf_spots.json'),
                           encoding='utf-8'))['spots']
    known = _known_shop_names(root)
    seen, found = set(), 0
    for sp in spots:
        params = urllib.parse.urlencode({
            'location': f"{sp['lat']},{sp['lng']}", 'radius': RADIUS,
            'keyword': '衝浪', 'language': 'zh-TW', 'key': key})
        raw = get(f'{ENDPOINT}/nearbysearch/json?{params}')
        if not raw:
            RV.flag(NAME, sp['name'], 'Places 查詢失敗'); continue
        try: res = json.loads(raw)
        except Exception as e:
            RV.flag(NAME, sp['name'], f'Places 回應非 JSON：{e}'); continue
        if res.get('status') not in ('OK', 'ZERO_RESULTS'):
            RV.flag(NAME, sp['name'],
                    f"Places 回應 {res.get('status')}：{res.get('error_message','')}")
            continue
        for r in res.get('results', []):
            pid = r.get('place_id')
            if not pid or pid in seen: continue
            seen.add(pid)
            rating, votes = r.get('rating'), r.get('user_ratings_total', 0)
            if not rating or rating < MIN_RATING or votes < MIN_REVIEWS: continue
            if _norm(r.get('name', '')) in known: continue        # 已收錄
            found += 1
            RV.flag(NAME, r.get('name', ''),
                    f"{sp['city']}・{sp['name']} 附近，評分 {rating}（{votes} 則）。"
                    f"確認後請補上服務內容再寫入名冊",
                    f"https://www.google.com/maps/place/?q=place_id:{pid}",
                    r.get('vicinity', ''))
    print(f'  （Places：{found} 家達 {MIN_RATING} 星／{MIN_REVIEWS} 則門檻，已列待驗證）')
    return []          # 只做發現，不直接進前台

def _known_shop_names(root):
    conf = json.load(open(os.path.join(root, 'data', 'indie_operators.json'),
                          encoding='utf-8'))
    out = set()
    for op in conf['operators']:
        out.add(_norm(op['name']))
        for part in op['name'].replace('（', ' ').replace('）', ' ').split():
            if len(part) >= 3: out.add(_norm(part))
    return out

def _norm(s):
    return ''.join((s or '').split()).lower()
