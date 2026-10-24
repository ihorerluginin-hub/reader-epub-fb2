# -*- coding: utf-8 -*-
"""Дополнительные визуальные проверки: fb2-стихи, панель оглавления, пустое состояние."""
import time, json, os, subprocess
import cdp

PORT = cdp.PORT
prof = os.path.join(os.environ.get('TEMP', '.'), 'edge-cdp-extra-%d' % int(time.time()))
proc = subprocess.Popen([cdp.EDGE, '--headless=new', '--disable-gpu', '--no-first-run',
    '--no-default-browser-check', '--remote-debugging-port=%d' % PORT,
    '--user-data-dir=' + prof, '--window-size=1300,900', 'about:blank'],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    cdp.wait_port(PORT)
    time.sleep(1.0)
    ws = cdp.new_tab('http://127.0.0.1:8321/index.html')
    cdp.WS = ws
    cdp.wait_title(ws, 'Ридер — книги без посредников', timeout=30)
    cdp.send('Runtime.enable'); cdp.send('Page.enable')

    # пустое состояние
    cdp.screenshot('shot-empty.png')

    # fb2 со стихами
    cdp.evaluate('''(async()=>{
      const r=await fetch('fixtures/sample.fb2');
      await window.__r.importFiles([new File([await r.arrayBuffer()],'sample.fb2')]);
    })()''')
    time.sleep(0.8)
    lib = cdp.evaluate("window.__r.idb.all().then(a=>a.map(b=>b.id))")
    cdp.evaluate("window.__r.openBook(%r)" % lib[0])
    time.sleep(1.0)
    cdp.evaluate("window.__r.turn(1)")
    time.sleep(0.9)
    cdp.screenshot('shot-fb2-poem.png')

    # панель оглавления
    cdp.evaluate("document.getElementById('tocBtn').click()")
    time.sleep(0.4)
    cdp.screenshot('shot-toc.png')

    # последняя страница (проверка правого поля)
    cdp.evaluate("document.getElementById('tocBtn').click(); window.__r.R.frac=1; window.__r.layout()")
    time.sleep(0.6)
    cdp.screenshot('shot-last-page.png')
    info = cdp.evaluate('''({maxScroll: window.__r.R.maxScroll, N: window.__r.R.N,
      sl: document.getElementById('scroller').scrollLeft,
      sw: document.getElementById('scroller').scrollWidth})''')
    print('last page info:', json.dumps(info))
    ws.close()
    print('EXTRA DONE')
finally:
    proc.kill()
