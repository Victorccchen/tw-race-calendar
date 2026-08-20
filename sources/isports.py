"""i運動資訊平台（教育部體育署）— 球類盃賽主來源。官方 REST，免 API key。"""
import json, re
from _http import get
import normalize as N

BASE = 'https://isports.sa.gov.tw/Api/Rest/V1/Activity.svc/GetActivityList'
NAME = 'i運動（體育署）'

def fetch(roc_begin='1150801', roc_end='1170731'):
    url = f'{BASE}?activityKind=1&activityDateBegin={roc_begin}&activityDateEnd={roc_end}&paging=true&pageSize=500&pageNo=1'
    raw = get(url)
    if not raw: return []
    try: rows = json.loads(raw).get('data', [])
    except Exception as e:
        print('  ! isports JSON 解析失敗', e); return []
    out = []
    for r in rows:
        nm = (r.get('activityName') or '').strip()
        if not N.is_cup(nm): continue          # 只留盃賽，排除聯賽
        d = N.roc_to_ad(r.get('activityDateBegin', ''))
        if not d: continue
        sp = N.sport_of(nm, (), r.get('activityType'))
        if not N.in_scope(sp): continue        # 只收拍類球運動與戶外耐力項目
        out.append(N.event(
            id='isp-'+r['activityNo'], name=nm, date=d,
            city=(r.get('activityCounty') or '').replace('台','臺'),
            location=r.get('activityCounty') or '',
            sport=sp,
            url=_url(r.get('activityWebsite')), source=NAME))
    return out

def _url(u):
    u = (u or '').strip()
    if not u: return ''
    if u.startswith(('http://','https://')): return u
    return 'https://' + u if re.match(r'^[\w.-]+\.[a-z]{2,}', u) else ''
