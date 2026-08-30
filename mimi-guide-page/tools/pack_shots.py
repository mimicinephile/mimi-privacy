#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
教學頁截圖打包 —— 把原圖轉成頁面要用的 WebP。

用法（在 D:\\MVP 底下跑）：
    python docs/mimi-guide-page/tools/pack_shots.py <原圖資料夾>

例：
    python docs/mimi-guide-page/tools/pack_shots.py D:/截圖

═══════════════════════════════════════════════════════════════════════════
🔑 檔名決定它去哪一格，不是順序。

   原圖檔名只要**開頭**是下面表格裡的代號就會被認出來，後面接什麼都行：
       02-showtimes-1.png
       02-showtimes-1 (1).PNG
       02-showtimes-1_final.jpg      ← 三個都會變成 assets/02-showtimes-1.webp

⚠ 沒對到的原圖會被列出來但**不會**被隨便塞進某一格 ——
  猜錯位置的截圖比缺一張更難發現：頁面看起來是滿的，只是講錯了。

🔴 跑完一定要看「還缺哪幾張」那一段。
   缺的那幾格會保留現有的佔位圖，而佔位圖在頁面上長得像一張正常的圖 ——
   不主動列出來的話，它會就這樣上線。
═══════════════════════════════════════════════════════════════════════════

⚠ 尺寸：輸出固定 596×1300（devices.css iphone-x 內框 298×650 的 2 倍）。
  原圖比例不同時以置中裁切（cover）處理 —— 手機截圖本來就接近這個比例。
⚠ 大小：品質從 88 起跳，逐級下修直到 ≤200KB（PRD §2）。
"""
import io
import os
import re
import sys

try:
    from PIL import Image
except ImportError:
    print('需要 Pillow：pip install Pillow')
    sys.exit(1)

W, H = 596, 1300
MAX_BYTES = 200 * 1024
HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.abspath(os.path.join(HERE, '..', 'assets'))

SLUGS = [
    # 🔑 Hero 目前直接沿用 04-house-1（小屋），沒有獨立檔案 ——
    #    同一張圖兩個檔名會多下載一次，而 hero 是 LCP。
    #    要換成專屬 hero 圖時把下面這行取消註解，並改 index.html 的 hero 區塊。
    # ('00-hero',         'Hero 主畫面'),
    ('01-start-1',      '開始使用：建立帳號（含邀請碼欄位）'),
    ('02-showtimes-1',  '查場次：附近影城'),
    ('02-showtimes-2',  '查場次：全部影城與縣市篩選'),
    ('02-showtimes-3',  '查場次：搜尋'),
    ('02-showtimes-4',  '查場次：影城時刻表'),
    ('03-tickets-1',    '票根：票根牆'),
    ('03-tickets-2',    '票根：蓋章'),
    ('03-tickets-3',    '票根：集章冊'),
    ('04-house-1',      '小屋：主畫面（展示櫃第 5 格需遮罩）'),
    ('04-house-2',      '小屋：收藏櫃'),
    ('04-house-3',      '小屋：佈置模式（展示櫃第 5 格需遮罩）'),
    ('05-blindbox-1',   '盲盒'),
    ('06-meetup-1',     '找影伴：加進願望清單'),
    ('06-meetup-2',     '找影伴：觀影配對'),
]
EXTS = {'.png', '.jpg', '.jpeg', '.webp', '.bmp', '.heic', '.tif', '.tiff'}


def cover(im):
    """置中裁切成 W×H，不變形。"""
    im = im.convert('RGB')
    sw, sh = im.size
    scale = max(W / sw, H / sh)
    nw, nh = round(sw * scale), round(sh * scale)
    im = im.resize((nw, nh), Image.LANCZOS)
    left, top = (nw - W) // 2, (nh - H) // 2
    return im.crop((left, top, left + W, top + H))


def save_under_cap(im, path):
    """品質逐級下修，直到檔案 ≤ MAX_BYTES。回傳 (bytes, quality)。"""
    for q in (88, 82, 76, 70, 64, 58, 52):
        buf = io.BytesIO()
        im.save(buf, 'WEBP', quality=q, method=6)
        if buf.tell() <= MAX_BYTES or q == 52:
            with open(path, 'wb') as f:
                f.write(buf.getvalue())
            return buf.tell(), q
    return 0, 0


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    src = sys.argv[1]
    if not os.path.isdir(src):
        print(f'找不到資料夾：{src}')
        return 1

    files = [f for f in sorted(os.listdir(src))
             if os.path.splitext(f)[1].lower() in EXTS]
    print(f'原圖資料夾 {src}：{len(files)} 個圖檔\n')

    done, unmatched = {}, list(files)
    for slug, label in SLUGS:
        # 開頭比對；同一格有多個候選時取檔名最短的（通常就是沒加後綴那個）
        cands = [f for f in files if re.match(re.escape(slug) + r'(\D|$)', f, re.I)]
        if not cands:
            continue
        pick = sorted(cands, key=len)[0]
        for c in cands:
            if c in unmatched:
                unmatched.remove(c)
        try:
            im = cover(Image.open(os.path.join(src, pick)))
        except Exception as e:
            print(f'  ✗ {slug:<16} 讀檔失敗 {pick}：{e}')
            continue
        size, q = save_under_cap(im, os.path.join(ASSETS, slug + '.webp'))
        flag = '' if size <= MAX_BYTES else '  ⚠ 仍超過 200KB'
        print(f'  ✓ {slug:<16} ← {pick}   {size/1024:6.1f} KB (q={q}){flag}')
        done[slug] = True

    missing = [(s, l) for s, l in SLUGS if s not in done]
    print()
    if missing:
        print(f'🔴 還缺 {len(missing)} 張 —— 這幾格目前仍是佔位圖，會就這樣上線：')
        for s, l in missing:
            print(f'     {s:<16} {l}')
    else:
        print(f'✅ {len(SLUGS)} 格全部到齊。')

    if unmatched:
        print(f'\n⚠ 有 {len(unmatched)} 個原圖沒對到任何一格（檔名開頭不符，未使用）：')
        for f in unmatched:
            print(f'     {f}')
        print('   對照上表把檔名開頭改成代號再跑一次。')

    print('\n⚠ 換完圖記得：確認 index.html 的 <html> 已移除 data-build="draft"。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
