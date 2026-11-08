"""Actual Chromium WebCrypto DOM verification on a local ephemeral demo server."""
from __future__ import annotations
import os,subprocess,sys,tempfile,socket,json,time,pathlib
import httpx
from playwright.sync_api import sync_playwright
from rgpu_terminal.journal import ReceiptJournal

ROOT=pathlib.Path(__file__).resolve().parents[1]

def run():
    with tempfile.TemporaryDirectory(prefix='innovulis-browser-') as d:
        j=ReceiptJournal(d)
        pub=j.public_key;fp=j.fingerprint;j.close()
        sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1];sock.close()
        token='browser-demo-token-'+('K'*48)
        env={**os.environ,'PYTHONPATH':str(ROOT),'INNOVULIS_OPERATOR_TOKEN':token,
             'INNOVULIS_SYNTHETIC_DEMO':'1'}
        p=subprocess.Popen([sys.executable,'-m','rgpu_terminal','serve','--data-dir',d,'--port',str(port)],
                           env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            url=f'http://127.0.0.1:{port}'
            for _ in range(100):
                try:
                    if httpx.get(url+'/api/health',timeout=.3).status_code==200:break
                except httpx.HTTPError:pass
                time.sleep(.08)
            else:raise RuntimeError('browser smoke server failed to start')
            errors=[]
            with sync_playwright() as pw:
                browser=pw.chromium.launch(headless=True,executable_path='/usr/bin/chromium',
                                            args=['--no-sandbox'])
                page=browser.new_page(viewport={'width':1550,'height':970},device_scale_factor=1)
                page.on('pageerror',lambda err:errors.append(str(err)))
                page.goto(url,wait_until='domcontentloaded')
                page.locator('#trustStatus').get_by_text('ANCHOR UNPINNED').wait_for(timeout=8000)
                assert 'VERIFIED' not in page.locator('#trustStatus').inner_text()
                page.locator('#pinPublic').fill(pub)
                page.locator('#pinFingerprint').fill(fp)
                page.locator('#pinKey').click()
                page.wait_for_function("document.querySelector('#chainState').textContent.includes('#1')",timeout=8000)
                assert 'ED25519 VERIFIED' in page.locator('#trustStatus').inner_text()
                page.locator('#operatorToken').fill(token)
                page.locator('#demoRefuted').click()
                page.wait_for_function("document.querySelector('#chainState').textContent.includes('#2')",timeout=8000)
                assert 'REFUTED_FALSE' in page.locator('#feed').inner_text()
                assert 'DEM' in page.locator('#joules').inner_text()
                assert page.locator('#qrcode img').count()==1
                page.screenshot(path=str(ROOT/'evidence/elite_browser_client_actual_webcrypto.png'),full_page=True)
                page.locator('#forgetKey').click()
                assert 'ANCHOR UNPINNED' in page.locator('#trustStatus').inner_text()
                browser.close()
            assert not errors, errors
            report={'real_chromium_webcrypto':'PASS', 'explicit_out_of_band_key_pin':'PASS',
                    'untrusted_before_pin':'PASS','real_signed_synthetic_refuted_card':'PASS',
                    'signed_qr_panel':'PASS','unpin_revokes_local_trust':'PASS',
                    'javascript_page_errors':errors,'physical_joules':'NOT_MEASURED'}
            print(json.dumps(report,sort_keys=True,indent=2))
            return report
        finally:
            p.terminate()
            try:p.wait(timeout=8)
            except subprocess.TimeoutExpired:p.kill()

if __name__=='__main__':run()
