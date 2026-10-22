"""Optional browser smoke test. Requires Playwright + Chromium; not a model trial.
Run: python3 tests/studio_browser.py --chromium /usr/bin/chromium
"""
import argparse
import json
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path
import sys
import tempfile
import threading

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from studio.server import App, handler
from test_studio import database_fixture, task_fixture


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--chromium')
    parser.add_argument('--screenshot')
    parser.add_argument('--offline-bridge', action='store_true', help='Render offline and bridge same-origin API through Python when browser networking is unavailable')
    args=parser.parse_args()
    from playwright.sync_api import sync_playwright, expect
    checks=[]
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp);db,run,data=database_fixture(root/'control')
        app=App(root/'studio',root/'control')
        server=ThreadingHTTPServer(('127.0.0.1',0),handler(app))
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch(executable_path=args.chromium,headless=True,args=['--no-sandbox'])
                page=browser.new_page(viewport={'width':1580,'height':1040},device_scale_factor=1)
                errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
                if args.offline_bridge:
                    def bridge(path, method, body):
                        if not path.startswith('/api/'):
                            raise ValueError('API paths only')
                        conn=HTTPConnection('127.0.0.1',server.server_port,timeout=5)
                        conn.request(method,path,body.encode('utf-8') if body else None,{'Authorization':'Bearer '+app.token,'Content-Type':'application/json'})
                        response=conn.getresponse();value={'status':response.status,'body':response.read().decode()};conn.close();
                        return value
                    page.expose_function('studioBridge',bridge)
                    static=Path(__file__).resolve().parents[1]/'tools/studio/static'
                    html=(static/'index.html').read_text().replace('<script type="module" src="/app.js"></script>','').replace('<link rel="stylesheet" href="/style.css">','')
                    page.set_content(html)
                    page.add_style_tag(content=(static/'style.css').read_text())
                    page.evaluate('''() => {
                      window.__downloads=[];
                      Object.defineProperty(window,'sessionStorage',{value:{getItem:()=>'',setItem:()=>{}}});
                      window.fetch=async(path,opts={})=>{if(window.__disconnect)throw Error('Injected disconnect');const r=await window.studioBridge(path,opts.method||'GET',opts.body||null);return new Response(r.body,{status:r.status,headers:{'Content-Type':'application/json'}})};
                      URL.createObjectURL=(blob)=>{window.__downloads.push(blob);return 'blob:offline-test'};
                      HTMLAnchorElement.prototype.click=function(){};
                    }''')
                    page.add_script_tag(content=(static/'app.js').read_text(),type='module')
                else:
                    page.goto(f'http://127.0.0.1:{server.server_port}/#token={app.token}')
                expect(page.locator('.node')).to_have_count(7);checks.append('canvas mounts seven real template nodes')
                assert '#token=' not in page.url;checks.append('offline page contains no URL token' if args.offline_bridge else 'access token removed from visible URL')
                card=page.locator('.node[data-id="implementer"]');before=card.get_attribute('style');box=card.bounding_box()
                page.mouse.move(box['x']+50,box['y']+25);page.mouse.down();page.mouse.move(box['x']+100,box['y']+50,steps=8);page.mouse.up()
                assert card.get_attribute('style')!=before;checks.append('drag moves canvas node')
                page.locator('#add-test').click();expect(page.locator('.node')).to_have_count(8);checks.append('add test updates graph')
                page.locator('#undo').click();expect(page.locator('.node')).to_have_count(7);checks.append('undo restores graph')
                page.locator('#import-task').click()
                page.locator('#file-input').set_input_files({'name':'task.json','mimeType':'application/json','buffer':json.dumps(task_fixture()).encode()})
                expect(page.locator('#title')).to_have_text('STUDIO_TEST_FIXTURE');checks.append('complete engine task imports')
                page.locator('#save').click();expect(page.locator('#revision')).to_contain_text('已保存版本');checks.append('immutable version saved')
                if args.offline_bridge:
                    page.locator('#compile').click();page.wait_for_function('window.__downloads.length > 0')
                    exported=json.loads(page.evaluate('window.__downloads[0].text()'))
                else:
                    with page.expect_download() as info:page.locator('#compile').click()
                    exported=json.loads(Path(info.value.path()).read_text())
                assert exported==task_fixture();checks.append('canvas exports exact engine configuration')
                assert page.locator('#start').is_disabled();checks.append('no operator permit means no browser execution')
                page.locator('#runs button').first.click();expect(page.locator('#context')).to_contain_text('只读')
                expect(page.locator('.node[data-id="reviewer"]')).to_contain_text('进程未证实');checks.append('stale RUNNING record not presented as alive')
                assert 'SECRET_PROMPT' not in page.content();checks.append('raw source/prompt not exposed')
                db.execute('UPDATE runs SET state=? WHERE id=?',('BLOCKED',run));db.commit()
                expect(page.locator('.node[data-id="reviewer"]')).to_have_class(__import__('re').compile('.*blocked.*'));checks.append('live polling observes committed WAL change')
                expect(page.locator('#rounds')).to_contain_text('NEEDS_CORRECTION');checks.append('historical review round displayed')
                assert page.locator('#save').is_disabled();checks.append('runtime canvas cannot write definitions')
                if args.offline_bridge:page.evaluate('window.__disconnect=true')
                else:page.route('**/api/runs',lambda route:route.abort())
                expect(page.locator('#connection')).to_contain_text('数据不可用');checks.append('lost connection visibly invalidates liveness')
                if args.offline_bridge:page.evaluate('window.__disconnect=false')
                else:page.unroute('**/api/runs')
                page.locator('#design-tab').click()
                assert not errors,errors;checks.append('no uncaught browser JavaScript errors')
                if args.screenshot:
                    # Capture the actual design UI, not a simulated live execution.
                    page.locator('#new').click();page.locator('#layout').click();page.wait_for_timeout(1200)
                    page.screenshot(path=args.screenshot,full_page=True)
                browser.close()
        finally:
            server.shutdown();server.server_close();thread.join();db.close()
    print(json.dumps({'browser_checks':len(checks),'passed':checks,'real_model_calls':0,'offline_http_bridge':args.offline_bridge},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
