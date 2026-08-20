"""中文日期解析。只回傳有信心的結果，模糊的一律回 None。"""
import re

# 2026年8月19日 / 115年5月8日 / 民國115年2月6日
FULL = re.compile(r'(?:民國\s*)?(\d{3,4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日?')
# 2026/8/19、2026-08-19
SLASH = re.compile(r'(20\d{2})[/\-.](\d{1,2})[/\-.](\d{1,2})')

def _norm_year(y):
    y = int(y)
    if 1900 < y < 2200: return y          # 西元
    if 100 <= y <= 199: return y + 1911   # 民國
    return None

def parse_all(text):
    """回傳文字中所有可解析的日期（YYYYMMDD），已排序去重。"""
    out = set()
    for m in FULL.finditer(text or ''):
        y = _norm_year(m.group(1))
        if not y: continue
        mm, dd = int(m.group(2)), int(m.group(3))
        if 1 <= mm <= 12 and 1 <= dd <= 31: out.add(f'{y}{mm:02d}{dd:02d}')
    for m in SLASH.finditer(text or ''):
        mm, dd = int(m.group(2)), int(m.group(3))
        if 1 <= mm <= 12 and 1 <= dd <= 31: out.add(f'{m.group(1)}{mm:02d}{dd:02d}')
    return sorted(out)

def first_after(text, keywords, window=170):
    """取「關鍵字之後」出現的第一個日期。

    不可用最小值 —— 賽事簡章常含年齡資格條款（例：報名資格：年滿十三歲
    (102年1月4日以前出生者)），那是出生日門檻，取最小值會被它汙染。
    """
    t = text or ''
    for kw in keywords:
        for m in re.finditer(re.escape(kw), t):
            seg = t[m.end(): m.end() + window]
            ds = _in_order(seg)
            if ds: return ds[0]
    return None

def _in_order(seg):
    hits = []
    for rx in (FULL, SLASH):
        for m in rx.finditer(seg):
            y = _norm_year(m.group(1))
            if not y: continue
            mm, dd = int(m.group(2)), int(m.group(3))
            if 1 <= mm <= 12 and 1 <= dd <= 31:
                hits.append((m.start(), f'{y}{mm:02d}{dd:02d}'))
    hits.sort()
    return [h[1] for h in hits]

def start_date(text, near=None, window=170):
    """賽事起日：優先取關鍵字之後的第一個日期。"""
    if near:
        d = first_after(text, near, window)
        if d: return d
        return None
    ds = parse_all(text)
    return ds[0] if ds else None

def plausible_reg(reg, event, max_lead_days=730):
    """報名截止的合理性檢查。

    賽事簡章裡的年齡分級條款（例：12歲級=2014年1月1日以後出生）會被誤抓成
    報名日期。規則：截止日必須早於賽期，且不得早於賽期前兩年。
    """
    if not (reg and event and len(reg) == 8 and len(event) == 8): return False
    if reg >= event: return False
    import datetime as _dt
    try:
        a = _dt.date(int(reg[:4]), int(reg[4:6]), int(reg[6:]))
        b = _dt.date(int(event[:4]), int(event[4:6]), int(event[6:]))
    except ValueError:
        return False
    return 0 < (b - a).days <= max_lead_days

RANGE_MD = re.compile(r'(\d{1,2})\s*[/.]\s*(\d{1,2})\s*[-–~至]\s*(\d{1,2})\s*[/.]\s*(\d{1,2})')

def cross_checked(text):
    """次要規則：沒有「比賽日期」標籤時使用，但要求兩個獨立訊號一致。

    國際賽公告常寫成「2026/9/13」搭配「9/13-9/20」。只有當西元日期的
    月日等於區間起日時才採用 —— 兩個來源互相印證才算數。
    注意公告時間戳是美式 M/D/YYYY，年份在後，不會被 SLASH 規則誤判。
    """
    t = text or ''
    cands = []
    for m in SLASH.finditer(t):
        y, mm, dd = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1 <= mm <= 12 and 1 <= dd <= 31: cands.append((y, mm, dd))
    if not cands: return None
    ranges = {(int(a), int(b)) for a, b, _, _ in RANGE_MD.findall(t)}
    if not ranges: return None
    for y, mm, dd in cands:
        if (mm, dd) in ranges:
            return f'{y}{mm:02d}{dd:02d}'
    return None

# 敘述句語序：「2026 年 5 月 17 日舉辦的 ForceKids…」日期在關鍵詞之前
BEFORE_KW = re.compile(
    r'(?:民國\s*)?(\d{3,4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日'
    r'\s*(?:即將|正式)?\s*(?:舉辦|舉行|登場|開跑|開賽|起跑)')

def narrative(text):
    """從公告敘述句取賽期。主辦方官網多為部落格式文章，日期寫在「舉辦」之前。"""
    for m in BEFORE_KW.finditer(text or ''):
        y = _norm_year(m.group(1))
        if not y: continue
        mm, dd = int(m.group(2)), int(m.group(3))
        if 1 <= mm <= 12 and 1 <= dd <= 31:
            return f'{y}{mm:02d}{dd:02d}'
    return None
