# -*- coding: utf-8 -*-
"""Генератор тестовых книг для проверки ридера."""
import zipfile, os, base64, zlib, struct

os.makedirs('fixtures', exist_ok=True)

def make_png(w, h, r, g, b):
    def chunk(t, d):
        return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    raw = b''
    for y in range(h):
        raw += b'\x00'
        for x in range(w):
            raw += bytes([(r + x) % 256, (g + y) % 256, b])
    ihdr = struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr) + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b'')

cover_png = make_png(120, 180, 60, 40, 140)
cover_b64 = base64.b64encode(cover_png).decode()

LONG = ('Текст главы для проверки пагинации. Lorem ipsum dolor sit amet, consectetur '
        'adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. '
        'Русский текст для проверки переносов: типографика, выключка, интерлиньяж. ')

def paras(n, start=1):
    return '\n'.join(f'<p>Абзац {i}. {LONG * 2}</p>' for i in range(start, start + n))

def xhtml(title, body):
    return f'''<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="ru" lang="ru">
<head><title>{title}</title></head>
<body>
<h2>{title}</h2>
{body}
</body>
</html>'''

# ---------------- EPUB ----------------
nav = '''<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head><title>Содержание</title></head>
<body>
<nav epub:type="toc"><h2>Содержание</h2><ol>
<li><a href="ch1.xhtml">Глава первая</a>
  <ol><li><a href="ch1.xhtml#mid">Середина первой</a></li></ol></li>
<li><a href="ch2.xhtml">Глава вторая</a></li>
<li><a href="ch3.xhtml">Глава третья</a></li>
</ol></nav>
</body>
</html>'''

ch1 = xhtml('Глава первая', f'''
<p><a href="ch2.xhtml#note1">Сноска во второй главе</a> — проверка внутренних ссылок.</p>
{paras(40)}
<p id="mid">Середина первой главы. {LONG * 2}</p>
{paras(40, 41)}
<p style="position:absolute;top:-9999px">Этот абзац со злым стилем должен был улететь за экран, но стиль срезан.</p>
<script>var evil = "скрипт из книги";</script>
<style>h2 {{ color: lime; }}</style>
''')

ch2 = xhtml('Глава вторая', f'''
{paras(60)}
<p id="note1"><b>Примечание 1.</b> Сюда должна вести ссылка из первой главы.</p>
{paras(30, 61)}
''')

ch3 = xhtml('Глава третья', f'''
{paras(50)}
<p><img src="img/cover.png" alt="иллюстрация"/> Изображение из архива выше.</p>
{paras(20, 51)}
''')

opf = f'''<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
<dc:identifier id="uid">urn:uuid:test-epub-001</dc:identifier>
<dc:title>Собрание тестовых сочинений</dc:title>
<dc:creator>Тестовый Автор</dc:creator>
<dc:language>ru</dc:language>
<dc:description>Описательная аннотация из метаданных: проверка титульного листа.</dc:description>
<meta name="cover" content="cover-img"/>
</metadata>
<manifest>
<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
<item id="cover-img" href="img/cover.png" media-type="image/png" properties="cover-image"/>
<item id="css" href="style.css" media-type="text/css"/>
<item id="c1" href="ch1.xhtml" media-type="application/xhtml+xml"/>
<item id="c2" href="ch2.xhtml" media-type="application/xhtml+xml"/>
<item id="c3" href="ch3.xhtml" media-type="application/xhtml+xml"/>
</manifest>
<spine>
<itemref idref="c1"/>
<itemref idref="c2"/>
<itemref idref="c3"/>
</spine>
</package>'''

container = '''<?xml version="1.0" encoding="utf-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
<rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles>
</container>'''

with zipfile.ZipFile('fixtures/sample.epub', 'w') as z:
    zi = zipfile.ZipInfo('mimetype')
    z.writestr(zi, 'application/epub+zip', compress_type=zipfile.ZIP_STORED)
    z.writestr('META-INF/container.xml', container)
    z.writestr('OEBPS/content.opf', opf)
    z.writestr('OEBPS/nav.xhtml', nav)
    z.writestr('OEBPS/style.css', 'body { color: red; }')
    z.writestr('OEBPS/ch1.xhtml', ch1)
    z.writestr('OEBPS/ch2.xhtml', ch2)
    z.writestr('OEBPS/ch3.xhtml', ch3)
    z.writestr('OEBPS/img/cover.png', cover_png)
print('sample.epub')

# ---------------- EPUB с DRM ----------------
with zipfile.ZipFile('fixtures/drm.epub', 'w') as z:
    zi = zipfile.ZipInfo('mimetype')
    z.writestr(zi, 'application/epub+zip', compress_type=zipfile.ZIP_STORED)
    z.writestr('META-INF/container.xml', container)
    z.writestr('META-INF/encryption.xml', '<?xml version="1.0"?><encryption xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><enc:EncryptedData xmlns:enc="http://www.w3.org/2001/04/xmlenc#"/></encryption>')
print('drm.epub')

# ---------------- FB2 ----------------
fb2 = f'''<?xml version="1.0" encoding="utf-8"?>
<FictionBook xmlns="http://www.gribuser.ru/xml/fictionbook/2.0" xmlns:l="http://www.w3.org/1999/xlink">
<description>
<title-info>
<author><first-name>Тестовый</first-name><last-name>Фб2шник</last-name></author>
<book-title>Камерная повесть о тестах</book-title>
<annotation><p>Аннотация с титульного листа: проверяем, что она попадает на обложку книги.</p></annotation>
<coverpage><image l:href="#cover.png"/></coverpage>
<lang>ru</lang>
</title-info>
</description>
<body>
<title><p>Камерная повесть о тестах</p></title>
<epigraph><p>Всё тестируемое тестируемо, а нетестируемое — тем более.</p><text-author>Народная мудрость</text-author></epigraph>
<section id="gl1">
<title><p>Глава первая, стихотворная</p></title>
<p>Текст с <emphasis>курсивом</emphasis> и <strong>жирным</strong>, а ещё <a l:href="#note1">сноска</a> в примечания.</p>
<subtitle>Подзаголовок по центру</subtitle>
<poem><title><p>Двустишие</p></title><stanza><v>Раз — читалка открыта,</v><v>Два — аккаунт не нужен.</v><v>Три — страница оффлайн,</v><v>Четыре — не тужат.</v></stanza></poem>
<empty-line/>
<image l:href="#cover.png"/>
{paras(45)}
</section>
<section id="gl2">
<title><p>Глава вторая, финальная</p></title>
{paras(55)}
<p>Конец книги. <a l:href="https://example.org/">Внешняя ссылка</a> должна открываться в новой вкладке.</p>
</section>
</body>
<body name="notes">
<section id="note1"><title><p>1</p></title><p>Примечание к сноске: сюда ведёт ссылка из первой главы.</p></section>
</body>
<binary id="cover.png" content-type="image/png">{cover_b64}</binary>
</FictionBook>'''

with open('fixtures/sample.fb2', 'wb') as f:
    f.write(fb2.encode('utf-8'))
print('sample.fb2')

# ---------------- FB2 в windows-1251 ----------------
fb2_1251 = '''<?xml version="1.0" encoding="windows-1251"?>
<FictionBook xmlns="http://www.gribuser.ru/xml/fictionbook/2.0">
<description><title-info>
<author><first-name>Старый</first-name><last-name>Кодировщик</last-name></author>
<book-title>Книга в одной двадцать пять первой</book-title>
<lang>ru</lang>
</title-info></description>
<body>
<section><title><p>Единственная глава</p></title>
<p>Если вы читаете это по-русски без кракозябр, значит кодировка windows-1251 распознана правильно.</p>
''' + ''.join(f'<p>Абзац {i}. {LONG}</p>' for i in range(1, 60)) + '''
</section>
</body>
</FictionBook>'''

with open('fixtures/sample-1251.fb2', 'wb') as f:
    f.write(fb2_1251.encode('cp1251'))
print('sample-1251.fb2')

# ---------------- FB2 в zip ----------------
with zipfile.ZipFile('fixtures/sample.fb2.zip', 'w', zipfile.ZIP_DEFLATED) as z:
    z.writestr('sample.fb2', fb2.encode('utf-8'))
print('sample.fb2.zip')

print('done')
