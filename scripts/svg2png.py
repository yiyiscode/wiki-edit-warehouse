"""svg2png: 用本機 Edge/Chrome 無頭模式把 SVG 轉成 PNG(不需額外套件)。

用法: python scripts/svg2png.py a.svg [b.svg ...]   -> 同目錄輸出 a.png
"""
import re
import subprocess
import sys
import tempfile
from pathlib import Path

# shortcut: 只找 Windows 常見安裝路徑, 換平台或自訂路徑時再擴充
BROWSERS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
]


def convert(svg: Path, scale: int = 2) -> Path:
    browser = next((b for b in BROWSERS if Path(b).exists()), None)
    if not browser:
        sys.exit("找不到 Edge/Chrome")
    text = svg.read_text(encoding="utf-8")
    m = re.search(r'viewBox="[\d.\-]+\s+[\d.\-]+\s+([\d.]+)\s+([\d.]+)"', text)
    if not m:
        sys.exit(f"{svg} 缺少 viewBox, 無法決定尺寸")
    w, h = int(float(m[1])), int(float(m[2]))
    out = svg.resolve().with_suffix(".png")
    # 包成 HTML 以固定尺寸並用白底
    html = (f'<html><body style="margin:0;background:#fff">'
            f'<img src="{svg.resolve().as_uri()}" width="{w}" height="{h}"></body></html>')
    with tempfile.TemporaryDirectory() as d:
        page = Path(d) / "p.html"
        page.write_text(html, encoding="utf-8")
        subprocess.run(
            [browser, "--headless", "--disable-gpu", "--hide-scrollbars",
             f"--force-device-scale-factor={scale}",
             f"--window-size={w},{h}", f"--screenshot={out}", page.as_uri()],
            check=True, capture_output=True, timeout=60)
    if not out.exists() or out.stat().st_size == 0:
        sys.exit(f"轉檔失敗: {svg}")
    return out


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    for f in sys.argv[1:]:
        print(convert(Path(f)))
