"""統一的賽事分類與正規化邏輯。所有來源都經過這裡。"""
import re

# 只收「拍類」球運動：網球、羽球、桌球、匹克球。
# 籃球／足球／棒壘球等資訊管道已普遍，不納入。
GOV = {'羽球活動':'badminton','桌球活動':'tabletennis','網球活動':'tennis',
       '水域活動':'swim','單車活動':'bike','跑步':'run','登山健行':'hike'}
BALL = [('badminton',r'羽球'),('tabletennis',r'桌球'),('tennis',r'網球'),
        ('pickleball',r'匹克球|pickleball')]
NAME = [('obstacle',r'斯巴達|spartan|障礙'),
        ('dive',r'潛水|自由潛水|freedive|scuba'),
        ('surf',r'衝浪|surf|SUP|立槳'),
        ('hike',r'登山|健行|百岳|縱走|郊山'),
        ('tri',r'鐵人|三項|triathlon|小鐵人|IRONKIDS|LAVAKIDS|PUSH ?BIKE|LAVA'),
        ('swim',r'泳渡|游泳|水域|渡水'),
        ('bike',r'自行車|單車|MTB|BikeDay|環法|KOM|騎行|車友|Étape'),
        ('trail',r'越野|trail|山徑|林道|健行|登山|野跑'),
        ('run',r'馬拉松|路跑|超馬|接力|健走|公里賽|跑步')]

KID   = re.compile(r'親子|兒童|小勇士|小鐵人|寶寶|幼兒|學童|國小|小學|童|kids|family|mini|米寶|青少年|中小學', re.I)
SHORT = re.compile(r'^(0\.?\d+|1|1\.5|2|2\.1|3|3\.3|3\.5)K$', re.I)
CAMP  = re.compile(r'營隊|兩日營|三日|夏令營|冬令營|課程|梯次|X-Camp|Camp|訓練營|體驗營')
EXP   = re.compile(r'體驗|推廣|嘉年華|同樂|樂園|闖關|健走|遊程|玩野|趣|Fun|fun|初階|入門|滑步車')
CUP   = re.compile(r'盃|杯|錦標賽|公開賽|邀請賽|挑戰賽|爭霸|大獎賽|排名賽')
LEAGUE= re.compile(r'聯賽|季賽|例行賽')
CITIES= ['基隆','臺北','新北','桃園','新竹','苗栗','臺中','彰化','南投','雲林','嘉義',
         '臺南','高雄','屏東','宜蘭','花蓮','臺東','澎湖','金門','連江']

def city_of(s):
    s = (s or '').replace('台','臺')
    return next((c for c in CITIES if c in s), '')

def sport_of(name, groups=(), gov=None):
    if gov and GOV.get(gov): return GOV[gov]
    for k, p in BALL:
        if re.search(p, name, re.I): return k
    s = name + ' ' + ' '.join(groups)
    for k, p in NAME:
        if re.search(p, s, re.I): return k
    return 'other'

def kind_of(name):
    if CAMP.search(name): return 'camp'
    if EXP.search(name):  return 'exp'
    return 'race'

def is_kid(name, groups=()):
    return bool(KID.search(name)) or any(KID.search(g) or SHORT.match(g) for g in groups)

def is_cup(name):
    return bool(CUP.search(name)) and not LEAGUE.search(name)

def roc_to_ad(d):
    """民國 115/08/01 或 1150801 → 20260801"""
    m = re.match(r'(\d{3})[/-]?(\d{2})[/-]?(\d{2})', d or '')
    return f"{int(m.group(1))+1911}{m.group(2)}{m.group(3)}" if m else ''

def event(id, name, date, city='', location='', groups=None, sport=None, kind=None,
          kid=None, reg_open='', reg_close='', status='', url='', source='', age='', fee=''):
    groups = groups or []
    name = (name or '').strip()
    return {
        'i': id, 'n': name, 'd': date, 'c': city or city_of(location),
        'l': (location or '')[:60], 'g': groups[:6],
        'k': 1 if (is_kid(name, groups) if kid is None else kid) else 0,
        's': sport or sport_of(name, groups),
        't': kind or kind_of(name),
        'ro': reg_open[:10], 'rc': reg_close[:10], 'st': status[:14],
        'u': url, 'src': source, 'a': age, 'f': fee,
    }

# ── 收錄範圍 ──
# 耐力型 + 拍類球運動 + 個人商戶常見的戶外項目。
ALLOWED = {'run','trail','tri','bike','swim','obstacle',      # 耐力
           'tennis','badminton','tabletennis','pickleball',   # 拍類
           'hike','surf','dive'}                              # 戶外／個人商戶

def in_scope(sport):
    return sport in ALLOWED
