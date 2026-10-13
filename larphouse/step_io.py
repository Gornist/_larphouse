"""Запись STEP с кириллицей в именах (\\X2\\…\\X0\\, ISO 10303-21)."""
import re
from build123d import export_step


def _step_text(m):
    """Не-ASCII символы в строках STEP -> \\X2\\hhhh\\X0\\ (ISO 10303-21)."""
    t = m.group(0)
    try:  # OCC пишет UTF-8, прочитанный как Latin-1 -> вернуть исходный текст
        t = t.encode('latin1').decode('utf-8')
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass
    return re.sub(r'[^\x00-\x7f]+',
                  lambda r: '\\X2\\' + ''.join('%04X' % ord(c) for c in r.group(0)) + '\\X0\\', t)


def save_step(shape, path):
    export_step(shape, path)
    txt = open(path, encoding='utf-8').read()
    txt = re.sub(r"'[^']*'", _step_text, txt)
    open(path, 'w', encoding='ascii').write(txt)
