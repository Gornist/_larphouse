"""Собрать документацию step/6 в один PDF.

Запуск:  python tools/make_pdf.py step/6 step/6/Модульные_дома.pdf
Нужны: pandoc, Chromium (headless).
"""
import os, re, subprocess, sys, tempfile

ORDER = ['README.md', 'ДЕТАЛИ.md', 'МОНТАЖ.md', '3х3/СБОРКА.md', '3х6/СБОРКА.md', '3х9/СБОРКА.md',
         '6х6/СБОРКА.md', 'ЗАКУПКА.md', '3х3/СПЕЦИФИКАЦИЯ_И_СМЕТА.md', '3х6/СПЕЦИФИКАЦИЯ_И_СМЕТА.md',
         '3х9/СПЕЦИФИКАЦИЯ_И_СМЕТА.md', '6х6/СПЕЦИФИКАЦИЯ_И_СМЕТА.md']
CHROME = '/opt/pw-browsers/chromium-1194/chrome-linux/chrome'

CSS = """
@page { size: A4; margin: 14mm 12mm 16mm 12mm; }
body { font-family: 'DejaVu Sans', sans-serif; font-size: 10pt; line-height: 1.4; color: #222; }
h1 { font-size: 19pt; border-bottom: 2px solid #8a5a2b; padding-bottom: 4px; margin-top: 0; }
h2 { font-size: 14pt; color: #5a3a1b; margin-top: 18px; }
h3 { font-size: 12pt; }
table { border-collapse: collapse; margin: 8px 0; width: auto; max-width: 100%; page-break-inside: avoid; }
th, td { border: 1px solid #bbb; padding: 3px 6px; vertical-align: top; }
th { background: #f1e7da; }
img { max-width: 100%; max-height: 120mm; }
td img { max-height: 70mm; }
pre { background: #f6f3ee; padding: 8px; font-size: 9pt; line-height: 1.15; page-break-inside: avoid; }
code { font-family: 'DejaVu Sans Mono', monospace; }
.pb { page-break-before: always; }
.cover { text-align: center; padding-top: 40mm; }
.cover h1 { border: none; font-size: 30pt; }
"""


def main(root, out):
    root = os.path.abspath(root)
    parts = [f'<div class="cover"><h1>Модульные игровые дома</h1>'
             f'<p style="font-size:14pt">Документация: детали, монтаж, сборка домов 3×3, 3×6, 3×9, 6×6, закупка</p>'
             f'<img src="file://{root}/6х6/img/дом.png" style="max-height:110mm"></div>']
    for rel in ORDER:
        path = os.path.join(root, rel)
        d = os.path.dirname(path)
        md = open(path, encoding='utf-8').read()
        # картинки — абсолютные пути; ссылки на другие .md — просто текст
        md = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)',
                    lambda m: f'![{m.group(1)}](file://{os.path.normpath(os.path.join(d, m.group(2)))})', md)
        md = re.sub(r'(?<!!)\[([^\]]+)\]\(([^)]+\.md)\)', r'\1', md)
        md = re.sub(r'(?<!!)\[([^\]]+)\]\((блоки/|\.\./)[^)]*\)', r'\1', md)
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


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
