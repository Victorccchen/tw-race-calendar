import time, urllib.request, urllib.error
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

def get(url, encoding='utf-8', timeout=30, retries=2):
    """抓網頁，失敗回 None（讓單一來源掛掉不會拖垮整個 pipeline）。"""
    for a in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode(encoding, errors='replace')
        except Exception as e:
            if a == retries:
                print(f"  ! 取得失敗 {url} → {e}")
                return None
            time.sleep(2 * (a + 1))
