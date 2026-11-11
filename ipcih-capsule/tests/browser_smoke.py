import asyncio,threading,json
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
from playwright.async_api import async_playwright
from ipcih.serve import Headers,ROOT

async def main():
    server=ThreadingHTTPServer(('127.0.0.1',0),partial(Headers,directory=str(ROOT)))
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        async with async_playwright() as p:
            browser=await p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
            page=await browser.new_page(viewport={'width':1440,'height':900})
            await page.goto(f'http://127.0.0.1:{server.server_port}/index.html')
            await page.locator('#pin').fill(Path('evidence/demo/pinned_pubkey_hex.txt').read_text())
            await page.locator('#wire').fill(Path('evidence/demo/signed_capsule.txt').read_text())
            await page.locator('#verify').click()
            await page.wait_for_function("document.querySelector('#status').textContent.includes('VERIFIED')", timeout=10000)
            assert await page.locator('#boot').is_enabled()
            assert not await page.locator('#runtime').is_visible()
            await page.locator('#boot').click()
            await page.wait_for_timeout(300)
            assert await page.locator('#runtime').is_visible()
            inner=page.frame_locator('#capsule')
            assert 'Sovereign Capsule' in await inner.locator('#claim').inner_text()
            await page.screenshot(path='evidence/demo/real_chromium_verified_capsule.png',full_page=True)
            await page.locator('#stop').click()
            assert not await page.locator('#runtime').is_visible()
            await page.locator('#pin').fill('11'*32)
            await page.locator('#verify').click()
            await page.wait_for_function("document.querySelector('#status').textContent.startsWith('REJECTED')",timeout=10000)
            assert not await page.locator('#boot').is_enabled()
            await browser.close()
            print('REAL_CHROMIUM_WEBCRYPTO_AND_SANDBOX=PASS; manual boot, controlled teardown, wrong pin fail-closed')
    finally:server.shutdown();server.server_close();thread.join()

if __name__=='__main__':asyncio.run(main())
