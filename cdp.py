# -*- coding: utf-8 -*-
"""CDP-драйвер для headless-проверки ридера."""
import json, os, socket, subprocess, sys, time, base64
import urllib.request
import websocket

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
PORT = 9334
WS = None
_id = 0

def wait_port(port, timeout=30):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            s = socket.create_connection(('127.0.0.1', port), 1)
            s.close()
            return True
        except OSError:
            time.sleep(0.3)
    raise RuntimeError('порт %d так и не открылся' % port)

def http_json(path, method='GET'):
    req = urllib.request.Request('http://127.0.0.1:%d%s' % (PORT, path), method=method)
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode('utf-8'))

def send(method, **params):
    global _id
    _id += 1
    mid = _id
    WS.send(json.dumps({'id': mid, 'method': method, 'params': params}))
    while True:
        msg = json.loads(WS.recv())
        if msg.get('id') == mid:
            if 'error' in msg:
                raise RuntimeError('%s: %s' % (method, msg['error']))
            return msg.get('result', {})

def evaluate(expr, await_promise=True):
    r = send('Runtime.evaluate', expression=expr, awaitPromise=await_promise,
             returnByValue=True, userGesture=True)
    if r.get('exceptionDetails'):
        raise RuntimeError('JS exception: %s' % json.dumps(r['exceptionDetails'])[:800])
    return r.get('result', {}).get('value')

def wait_title(tab_ws, want, timeout=60):
    global WS
    WS = tab_ws
    send('Runtime.enable')
    send('Page.enable')
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            v = evaluate('document.title')
            if v == want:
                return
        except Exception:
            pass
        time.sleep(0.5)
    raise RuntimeError('title %r не дождались' % want)

def new_tab(url):
    r = http_json('/json/new?%s' % url, method='PUT')
    ws = websocket.create_connection(r['webSocketDebuggerUrl'], timeout=120)
    return ws

def screenshot(path, w=1300, h=900):
    b64 = send('Page.captureScreenshot', format='png')['data']
    with open(path, 'wb') as f:
        f.write(base64.b64decode(b64))
    print('shot ->', path)

def main():
    prof = os.path.join(os.environ.get('TEMP', '.'), 'edge-cdp-profile-%d' % int(time.time()))
    proc = subprocess.Popen([EDGE,
        '--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
        '--remote-debugging-port=%d' % PORT, '--user-data-dir=' + prof,
        '--window-size=1300,900', 'about:blank'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        wait_port(PORT)
        time.sleep(1.0)

        # --- харнесс со всеми сценариями ---
        ws1 = new_tab('http://127.0.0.1:8321/test.html')
        try:
            wait_title(ws1, 'HARNESS-DONE', timeout=90)
            global WS; WS = ws1
            print('==== HARNESS OUTPUT ====')
            print(evaluate("document.getElementById('out').textContent"))
            print('==== END ====')
        finally:
            ws1.close()

        # --- визуальная проверка ---
        ws2 = new_tab('http://127.0.0.1:8321/index.html')
        WS = ws2
        wait_title(ws2, 'Ридер — книги без посредников', timeout=30)
        send('Runtime.enable'); send('Page.enable')
        time.sleep(0.5)
        evaluate('''(async()=>{
          const books=[];
          for(const [u,n] of [['fixtures/sample.epub','sample.epub'],['fixtures/sample.fb2','sample.fb2'],['fixtures/sample-1251.fb2','book-1251.fb2']]){
            const r=await fetch(u); books.push(new File([await r.arrayBuffer()],n));
          }
          await window.__r.importFiles(books);
        })()''')
        time.sleep(1.0)
        screenshot('shot-library.png')

        lib = evaluate("window.__r.idb.all().then(a=>a.map(b=>({id:b.id,fmt:b.fmt,title:b.title,author:b.author,cover:!!b.cover})))")
        print('library:', json.dumps(lib, ensure_ascii=False))
        epub = [b for b in lib if b['fmt'] == 'epub'][0]
        evaluate("window.__r.openBook(%r)" % epub['id'])
        time.sleep(1.2)
        screenshot('shot-epub-start.png')
        evaluate("window.__r.turn(1); window.__r.turn(1)")
        time.sleep(1.0)
        screenshot('shot-epub-p3.png')
        # тёмная тема + санс
        evaluate("window.__r.S.theme='dark'; window.__r.S.font='sans'; window.__r.applySettings(); window.__r.layout()")
        time.sleep(0.4)
        screenshot('shot-epub-dark.png')
        # fb2
        fb2 = [b for b in lib if b['title'].includes('Камерная')] if False else [b for b in lib if 'Камерная' in b['title']]
        evaluate("window.__r.backToLibrary()")
        time.sleep(0.5)
        evaluate("window.__r.openBook(%r)" % fb2[0]['id'])
        time.sleep(1.2)
        evaluate("window.__r.S.theme='sepia'; window.__r.S.font='serif'; window.__r.applySettings(); window.__r.layout()")
        time.sleep(0.4)
        screenshot('shot-fb2.png')
        ws2.close()
        print('VISUAL DONE')
    finally:
        proc.kill()

if __name__ == '__main__':
    main()
