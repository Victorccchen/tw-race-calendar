"""Google Places：依浪點座標搜尋高評價衝浪店家。

Google Maps 的評分無法從網頁取得（爬 Maps 違反其服務條款），必須走官方
Places API。因此本模組需要環境變數 GOOGLE_MAPS_API_KEY；未設定時整個
來源會安靜略過，不影響其他來源。

只收評分達門檻、且評論數足夠的店家 —— 五顆星但只有 3 則評論不算高評價。
API 只提供店家層級資訊（名稱、地址、評分、電話、官網），不含課程與價目，
因此撈到的店家一律進待驗證佇列，由人工補上服務內容後才進前台。
"""
import os, re, json, urllib.parse
from _http import get
import review as RV

NAME = 'Google Places'
ENDPOINT = 'https://maps.googleapis.com/maps/api/place'
MIN_RATING = float(os.environ.get('PLACES_MIN_RATING', '4.8'))
MIN_REVIEWS = int(os.environ.get('PLACES_MIN_REVIEWS', '800'))
RADIUS = 3000

# 只收運動旅遊／戶外活動業者，排除餐飲與旅宿。
# 注意：types 不能單獨判斷 —— 不少衝浪店附設住宿會被標成 lodging
#（極酷衝浪、野孩子衝浪社皆是），純用類型排除會誤刪。因此改用
# 「名稱有活動訊號」為主，types 只用來剔除明確的餐飲業。
ACTIVITY = re.compile(
    r'衝浪|surf|SUP|立槳|paddle|潛水|dive|freediv|獨木舟|kayak|canoe|溯溪|浮潛|snorkel|'
    r'泛舟|rafting|滑水|風箏|kite|帆船|sail|攀岩|climb|抱石|boulder|'
    r'單車|自行車|腳踏車|bike|cycl|登山|健行|嚮導|guide|hiking|trek|飛行傘|paraglid|'
    r'教練|俱樂部|學校|基地|探索|運動|戶外|工作室|club|school|academy|outdoor|adventure', re.I)
FOOD_LODGING = re.compile(
    r'咖啡|cafe|餐廳|食堂|小吃|麵包|甜點|肉桂|燒烤|居酒屋|酒吧|'
    r'民宿|旅店|旅館|飯店|背包|hostel|hotel|inn|共居|co-?living|營地|露營區', re.I)
FOOD_TYPES = {'restaurant', 'cafe', 'bakery', 'bar', 'food', 'meal_takeaway',
              'meal_delivery', 'night_club', 'convenience_store', 'supermarket'}

# 只收「帶團體驗」業者，排除純租賃與零售。
# 觀光區的電動自行車出租、登山裝備行雖然評分高、評論多，但賣的是器material
# 不是體驗 —— 對想找活動的人沒有意義。
RENTAL_RETAIL = re.compile(
    r'出租|租賃|租借|租車|車行|電動自行車|電動車|腳踏車行|'
    r'裝備|用品|專賣|工廠|商行|百貨|直營|批發|五金', re.I)
EXPERIENCE = re.compile(
    r'體驗|教學|課程|導覽|嚮導|帶團|訓練|營隊|學校|俱樂部|探索|工作室|中心|'
    r'潛水|dive|泛舟|raft|溯溪|溪降|攀岩|climb|抱石|boulder|衝浪|surf|'
    r'立槳|SUP|paddle|獨木舟|kayak|帆船|sail|飛行傘|paraglid|school|academy|club', re.I)

def _rare_conf(root):
    f = os.path.join(root, 'data', 'rare_activities.json')
    if not os.path.exists(f): return None
    return json.load(open(f, encoding='utf-8'))


def check_rarity(keyword, key, region='台灣'):
    """實際查證某活動全台有幾家同業。用來維護稀有清單，不在每日流程跑。"""
    q = urllib.parse.urlencode({'query': f'{region} {keyword}', 'language': 'zh-TW', 'key': key})
    raw = get(f'{ENDPOINT}/textsearch/json?{q}')
    if not raw: return None
    try: res = json.loads(raw)
    except Exception: return None
    return len(res.get('results', []))


def fetch():
    key = os.environ.get('GOOGLE_MAPS_API_KEY')
    if not key:
        print('  （未設定 GOOGLE_MAPS_API_KEY，略過 Places 搜尋）')
        return []
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    spots = json.load(open(os.path.join(root, 'data', 'surf_spots.json'),
                           encoding='utf-8'))['spots']
    known = _known_shop_names(root)
    rare_conf = _rare_conf(root)
    seen, found = set(), 0
    queries = [(sp, kw) for sp in spots for kw in sp.get('keywords', ['戶外'])]
    print(f'  （Places：{len(spots)} 個熱點 × 關鍵字，共 {len(queries)} 次查詢）')
    for sp, kw in queries:
        params = urllib.parse.urlencode({
            'location': f"{sp['lat']},{sp['lng']}", 'radius': sp.get('radius', RADIUS),
            'keyword': kw, 'language': 'zh-TW', 'key': key})
        raw = get(f'{ENDPOINT}/nearbysearch/json?{params}')
        if not raw:
            RV.flag(NAME, f"{sp['name']}／{kw}", 'Places 查詢失敗'); continue
        try: res = json.loads(raw)
        except Exception as e:
            RV.flag(NAME, f"{sp['name']}／{kw}", f'Places 回應非 JSON：{e}'); continue
        if res.get('status') not in ('OK', 'ZERO_RESULTS'):
            RV.flag(NAME, f"{sp['name']}／{kw}",
                    f"Places 回應 {res.get('status')}：{res.get('error_message','')}")
            continue
        for r in res.get('results', []):
            pid = r.get('place_id')
            if not pid or pid in seen: continue
            seen.add(pid)
            name = r.get('name', '')
            if _is_known(name, known): continue                    # 已收錄（含名稱變體）
            types = set(r.get('types', []))
            if types & FOOD_TYPES: continue                        # 明確的餐飲業
            if FOOD_LODGING.search(name) and not ACTIVITY.search(name):
                continue                                           # 純餐飲或住宿
            if not ACTIVITY.search(name) and 'store' not in types:
                continue                                           # 看不出是活動業者
            if RENTAL_RETAIL.search(name) and not EXPERIENCE.search(name):
                continue                                           # 純租賃或零售，不提供體驗
            rating, votes = r.get('rating'), r.get('user_ratings_total', 0)
            if not rating: continue
            rare = _rare_match(name, rare_conf)
            if rare:
                if rating < (rare_conf or {}).get('min_rating', 4.0): continue
            elif rating < MIN_RATING or votes < MIN_REVIEWS:
                continue
            found += 1
            tag = f'【稀有・{rare}】' if rare else ''
            RV.flag(NAME, name,
                    f"{tag}{sp['city']}・{sp['name']}（搜尋「{kw}」）評分 {rating}（{votes} 則）。"
                    f"確認後請補上服務內容再寫入名冊",
                    f"https://www.google.com/maps/place/?q=place_id:{pid}",
                    r.get('vicinity', ''))
    print(f'  （Places：{found} 家達 {MIN_RATING} 星／{MIN_REVIEWS} 則門檻，已列待驗證）')
    return []          # 只做發現，不直接進前台

def _is_known(name, known):
    """比對是否已收錄。Google 上的商家名常帶服務說明後綴
    （「洄遊吧食魚體驗館」vs 名冊裡的「洄遊吧 FishBar」），
    完整字串比不出來，改取開頭連續中文作為核心名。"""
    n = _norm(name)
    core = _core(name)
    for k in known:
        if not k: continue
        if k in n or n in k: return True
        if core and len(core) >= 3 and (core in k or k.startswith(core)): return True
    return False


def _core(s):
    m = re.match(r'[\u4e00-\u9fff]{2,10}', (s or '').strip())
    return m.group(0) if m else ''


def _known_shop_names(root):
    conf = json.load(open(os.path.join(root, 'data', 'indie_operators.json'),
                          encoding='utf-8'))
    out = set()
    for op in conf['operators']:
        out.add(_norm(op['name']))
        # 取中文主體（去掉英文與空白），用來比對 Google 上的名稱變體
        zh = re.sub(r'[a-zA-Z0-9\s\-_.·．（）()]+', '', op['name'])
        if len(zh) >= 3: out.add(_norm(zh))
        c = _core(op['name'])
        if len(c) >= 3: out.add(_norm(c))
    return out

def _norm(s):
    return ''.join((s or '').split()).lower()


def _rare_match(name, conf):
    """名稱是否命中稀有活動；回傳活動標籤或 None。"""
    if not conf: return None
    for a in conf.get('activities', []):
        if re.search(a['keyword'], name or '', re.I): return a['label']
    return None
