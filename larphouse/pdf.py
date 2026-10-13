"""Собрать документацию (docs/ и houses/*) в один PDF.

  python -m larphouse pdf          # -> docs/modular_houses.pdf
Нужны: pandoc, Chromium (headless).
"""
import glob, os, re, subprocess, tempfile

from .config import HOUSES
from .paths import ROOT, PDF

ORDER = (['docs/README.md', 'docs/parts.md', 'docs/installation.md'] +
         [f'houses/{k}/assembly.md' for k in HOUSES] + ['docs/purchasing.md'] +
         [f'houses/{k}/estimate.md' for k in HOUSES])
CHROME = next((p for p in (*sorted(glob.glob('/opt/pw-browsers/chromium-*/chrome-linux/chrome')),
                           '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
                           '/Applications/Chromium.app/Contents/MacOS/Chromium') if os.path.exists(p)),
              'chromium')

CSS = """
@page { size: A4; margin: 14mm 12mm 16mm 12mm; }
body { font-family: 'DejaVu Sans', Arial, sans-serif; font-size: 10pt; line-height: 1.4; color: #222; }
h1 { font-size: 19pt; border-bottom: 2px solid #8a5a2b; padding-bottom: 4px; margin-top: 0; }
h2 { font-size: 14pt; color: #5a3a1b; margin-top: 18px; }
h3 { font-size: 12pt; }
table { border-collapse: collapse; margin: 8px 0; width: auto; max-width: 100%; page-break-inside: avoid; }
th, td { border: 1px solid #bbb; padding: 3px 6px; vertical-align: top; }
th { background: #f1e7da; }
img { max-width: 100%; max-height: 120mm; }
td img { max-height: 70mm; }
pre { background: #f6f3ee; padding: 8px; font-size: 9pt; line-height: 1.15; page-break-inside: avoid; }
code { font-family: 'DejaVu Sans Mono', Menlo, monospace; }
.pb { page-break-before: always; }
.cover { text-align: center; padding-top: 40mm; }
.cover h1 { border: none; font-size: 30pt; }
"""


def make_pdf(out=PDF, root=ROOT):
    parts = [f'<div class="cover"><h1>Модульные игровые дома</h1>'
             f'<p style="font-size:14pt">Документация: детали, монтаж, сборка домов 3×3, 3×6, 3×9, 6×6, закупка</p>'
             f'<img src="file://{root}/houses/6x6/img/house.png" style="max-height:110mm"></div>']
    for rel in ORDER:
        path = os.path.join(root, rel)
        d = os.path.dirname(path)
        md = open(path, encoding='utf-8').read()
        # картинки — абсолютные пути; ссылки на свои файлы — просто текст
        md = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)',
                    lambda m: f'![{m.group(1)}](file://{os.path.normpath(os.path.join(d, m.group(2)))})', md)
        md = re.sub(r'(?<!!)\[([^\]]+)\]\((?!https?:)[^)]*\)', r'\1', md)
        html = subprocess.run(['pandoc', '-f', 'gfm', '-t', 'html'], input=md, capture_output=True,
                              text=True, check=True).stdout
        parts.append(f'<div class="pb">{html}</div>')
    doc = (f'<!doctype html><html lang="ru"><head><meta charset="utf-8"><title>Модульные игровые дома</title>'
           f'<style>{CSS}</style></head><body>{"".join(parts)}</body></html>')
    with tempfile.NamedTemporaryFile('w', suffix='.html', delete=False, encoding='utf-8') as f:
        f.write(doc)
        tmp = f.name
    subprocess.run([CHROME, '--headless=new', '--no-sandbox', '--disable-gpu', '--allow-file-access-from-files',
                    f'--print-to-pdf={os.path.abspath(out)}', '--no-pdf-header-footer', f'file://{tmp}'],
                   check=True, capture_output=True)
    os.unlink(tmp)
