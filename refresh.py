#!/usr/bin/env python3
"""每日刷新：抓取全來源 → 快照訂版 → 比對異動 → 產出清單 → 重建網站。

  python3 refresh.py            # 完整跑一次
  python3 refresh.py --no-links # 跳過連結檢查（較快）
  python3 refresh.py --dry      # 只比對不寫入
"""
import sys, os, json, argparse, datetime, concurrent.futures as cf
import urllib.request, urllib.error

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(ROOT, 'lib'), os.path.join(ROOT, 'sources')]
import diff as D
import review as RV
import normalize as N
from _http import UA

SOURCES = ['biji', 'isports', 'kktix', 'ctta', 'sunmoonlake', 'indie']
DATA, SNAP, CHG, SITE = (os.path.join(ROOT, p) for p in
                         ('data', 'data/snapshots', 'data/changes', 'site'))
REVIEW = os.path.join(ROOT, 'data', 'review')
WEB    = os.path.join(ROOT, 'web')
# 路跑規模門檻。運動筆記僅 13% 的賽事頁有「名額」欄位，不足以當篩選依據；
# 列表頁的「收藏數」覆蓋 87%，且排序與實際賽事規模高度吻合
# （田中馬 210≈1.6萬人、臺北馬 203≈2.8萬人、板橋馬 121≈8千人）。
# 校準後收藏 30 ≈ 3,000 人。越野賽本就數百人規模，不套用。
MIN_RUN_POP = 30

def collect():
    all_ev, report = [], []
    for name in SOURCES:
        try:
            mod = __import__(name)
            rows = mod.fetch() or []
            all_ev += rows
            report.append((name, getattr(mod, 'NAME', name), len(rows), None))
            print(f"  {getattr(mod,'NAME',name):20s} {len(rows):4d} 筆")
        except Exception as e:
            report.append((name, name, 0, str(e)))
            print(f"  {name:20s} ✗ {e}")
    # 去重：同 id 保留欄位較完整者
    best = {}
    for e in all_ev:
        cur = best.get(e['i'])
        if not cur or _score(e) > _score(cur): best[e['i']] = e
    today = datetime.date.today().strftime('%Y%m%d')
    kept, dropped, small, pending = [], 0, 0, 0
    for e in best.values():
        if e.get('sv'):                       # 店家常態服務：無日期、全年提供
            kept.append(e); continue
        if e['d'] < today: continue
        if not N.in_scope(e['s']):            # 收錄範圍外（非拍類球運動等）
            dropped += 1; continue
        if e['s'] == 'run':                   # 路跑數量龐雜，只留具規模的場次
            pop = e.get('p')
            if pop is None: pending += 1       # 新上架、尚無收藏數，暫予保留
            elif pop < MIN_RUN_POP:
                small += 1; continue
        kept.append(e)
    if dropped: print(f"  （範圍外略過 {dropped} 筆）")
    if small:   print(f"  （路跑規模不足略過 {small} 筆，門檻 收藏≥{MIN_RUN_POP}）")
    if pending: print(f"  （路跑新上架無收藏數 {pending} 筆，暫予保留）")
    return sorted(kept, key=lambda e: e['d']), report

def _score(e):
    return sum(1 for k in ('rc','ro','g','l','u','a','f') if e.get(k))

def check_links(events, limit=90):
    """只檢查最相關的（近期且可報名的）連結，避免每天打爆對方伺服器。"""
    targets = [e for e in events if e['u'].startswith('http')][:limit]
    dead = []
    def probe(e):
        req = urllib.request.Request(e['u'], headers={'User-Agent': UA}, method='HEAD')
        try:
            with urllib.request.urlopen(req, timeout=12) as r:
                if r.status >= 400: return (e['i'], f"HTTP {r.status}")
        except urllib.error.HTTPError as ex:
            if ex.code in (403, 405): return None          # 拒絕 HEAD ≠ 失效
            return (e['i'], f"HTTP {ex.code}")
        except Exception as ex:
            return (e['i'], f"連線失敗：{type(ex).__name__}")
        return None
    with cf.ThreadPoolExecutor(max_workers=6) as ex:
        for r in ex.map(probe, targets):
            if r: dead.append(r)
    return dead

def build_site(events):
    tpl = open(os.path.join(SITE, 'template.html'), encoding='utf-8').read()
    data = json.dumps(events, ensure_ascii=False, separators=(',', ':'))
    html = tpl.replace('__DATA__', data)
    out = os.path.join(SITE, 'index.html')
    open(out, 'w', encoding='utf-8').write(html)
    # Vercel 部署目錄：靜態頁 + ICS 端點要用的資料
    os.makedirs(os.path.join(WEB, 'public'), exist_ok=True)
    os.makedirs(os.path.join(WEB, 'data'), exist_ok=True)
    open(os.path.join(WEB, 'public', 'index.html'), 'w', encoding='utf-8').write(html)
    json.dump(events, open(os.path.join(WEB, 'data', 'events.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, separators=(',', ':'))
    return out, len(html.encode())

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--no-links', action='store_true')
    ap.add_argument('--dry', action='store_true')
    a = ap.parse_args()
    today = datetime.date.today().isoformat()
    print(f"═══ 每日刷新 {today} ═══\n抓取來源：")
    events, report = collect()
    sv = sum(1 for e in events if e.get("sv"))
    print(f"\n合併後 {len(events)-sv} 場賽事 + {sv} 項店家服務")

    dead = [] if a.no_links else check_links(events)
    if dead: print(f"連結檢查：{len(dead)} 個異常")

    prev_file = os.path.join(DATA, 'events.json')
    prev = json.load(open(prev_file, encoding='utf-8')) if os.path.exists(prev_file) else []
    changes = D.compare(prev, events, dead, today=datetime.date.today().strftime('%Y%m%d'))
    print(f"偵測到 {len(changes)} 筆異動")

    if a.dry:
        print(D.to_markdown(changes, today, {'total': len(events)}))
        print(RV.to_markdown(today)); return

    json.dump(events, open(os.path.join(SNAP, f'{today}.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, separators=(',', ':'))        # 訂版：每日快照永久保存
    json.dump(events, open(prev_file, 'w', encoding='utf-8'),
              ensure_ascii=False, separators=(',', ':'))
    md = D.to_markdown(changes, today, {'total': len(events)})
    open(os.path.join(CHG, f'{today}.md'), 'w', encoding='utf-8').write(md)
    os.makedirs(REVIEW, exist_ok=True)
    rv = RV.items()
    open(os.path.join(REVIEW, f'{today}.md'), 'w', encoding='utf-8').write(RV.to_markdown(today))
    json.dump(changes, open(os.path.join(CHG, f'{today}.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    path, size = build_site(events)
    print(f"\n✅ 快照 data/snapshots/{today}.json")
    print(f"✅ 異動清單 data/changes/{today}.md（{len(changes)} 筆）")
    print(f"✅ 網站 {path}（{size/1048576:.2f} MB）")
    print(f"✅ 待驗證 data/review/{today}.md（{len(rv)} 筆）")

if __name__ == '__main__':
    main()
