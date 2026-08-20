"""待人工驗證佇列。抓到但無法確信的資料不進資料庫，改列在這裡。

寧缺勿濫：前台只放能驗證的資料；不確定的東西必須被看見，而不是被丟掉。
"""
_Q = []

def flag(source, name, reason, url='', raw=''):
    _Q.append(dict(source=source, name=name[:80], reason=reason, url=url, raw=raw[:120]))

def items(): return list(_Q)
def clear(): _Q.clear()

def to_markdown(date):
    if not _Q:
        return f"# 待驗證佇列 · {date}\n\n沒有需要人工確認的項目。\n"
    md = [f"# 待驗證佇列 · {date}", "",
          f"以下 **{len(_Q)}** 筆需要人工看一眼。原因分兩種：**整筆未收**（資料不足，"
          f"不進前台），或**部分欄位捨棄**（賽事已收錄，但某個欄位不可信）。",
          "個人商戶的場次確認後補進 `data/indie_operators.json`；解析問題請修對應規則。", ""]
    bysrc = {}
    for it in _Q: bysrc.setdefault(it['source'], []).append(it)
    for src, rows in bysrc.items():
        md += [f"## {src}（{len(rows)} 筆）", "", "| 賽事 | 未收原因 | 原始片段 |", "|---|---|---|"]
        for r in rows:
            n = f"[{r['name']}]({r['url']})" if r['url'] else r['name']
            md.append(f"| {n} | {r['reason']} | {r['raw'] or '—'} |")
        md.append("")
    return '\n'.join(md)
