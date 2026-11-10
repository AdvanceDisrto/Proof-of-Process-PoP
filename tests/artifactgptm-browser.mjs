import assert from "node:assert/strict";
import { chromium } from "playwright";

const browser = await chromium.launch({headless:true,args:["--no-sandbox"]});
try{
 const page=await browser.newPage({viewport:{width:1365,height:900}});
 const errors=[];
 page.on("pageerror",e=>errors.push(e.message));
 const response=await page.goto("https://artifactgptm.com/",{waitUntil:"domcontentloaded",timeout:45000});
 assert.equal(response.status(),200,"Production HTML must be served over HTTPS");
 await page.locator("canvas.matrix-tunnel-canvas").waitFor();
 await page.getByRole("heading",{name:/Just Ask Buddy/i}).waitFor();
 console.log("MAIN DOMAIN UI PASS",response.status());

 const snapshot=()=>page.locator("canvas.matrix-tunnel-canvas").evaluate(e=>e.toDataURL("image/png"));
 const before=await snapshot(); await page.waitForTimeout(900);const after=await snapshot();
 assert.notEqual(before,after,"Realtime Matrix must animate");
 console.log("PRODUCTION MATRIX ANIMATION PASS");

 const clock=page.locator("time.matrix-utc-clock");
 await clock.waitFor();
 const first=await clock.textContent();await page.waitForTimeout(1400);
 const second=await clock.textContent();assert.notEqual(first,second,"UTC clock must tick");
 assert.match(second,/UTC$/);
 console.log("LIVE UTC CLOCK PASS",second);

 const mic=page.getByRole("button",{name:/Start microphone with permission/i});
 await mic.waitFor();assert.equal(await mic.getAttribute("aria-pressed"),"false");
 await page.getByRole("button",{name:/ENABLE SPOKEN REPLIES/i}).waitFor();
 console.log("PERMISSION-GATED MIC + SPOKEN REPLIES CONTROLS PRESENT PASS");

 const news=page.getByRole("region",{name:"Global Intel Feed"});
 await news.waitFor();
 // Attributed news is fetched live. Fail honestly if upstream is down.
 await page.waitForTimeout(5500);
 const items=await news.locator("article").count();
 assert.ok(items>0,"At least one actual publisher headline should be shown");
 const href=await news.locator("article a").first().getAttribute("href");
 assert.match(href,/^https:\/\//);
 console.log("REAL SOURCE-LINKED INTEL UI PASS",items);
 const verifyNav=page.locator('nav[aria-label="Main workspace"] button').filter({hasText:"Verify"}).first();
 await verifyNav.click();
 console.log("AFTER VERIFY CLICK", await page.evaluate(() => ({url:location.href, selected:[...document.querySelectorAll('button.selected')].map(x=>x.textContent),text:document.querySelector('.matrix-center')?.innerText?.slice(0,1800),scripts:[...document.scripts].map(x=>x.src).filter(Boolean)})));
 await page.getByRole("heading",{name:"Authenticated Evidence Index"}).waitFor({timeout:7000});
 const gate=page.getByRole("region",{name:"Authenticated CIH receipt integration"});
 await gate.waitFor();
 assert.ok((await gate.textContent()).includes("AUTH0"),"Auth0 configuration status must be shown");
 assert.equal(await gate.getByRole("button",{name:"ISSUE AUTHENTICATED RECEIPT"}).isDisabled(),true,
   "Receipt issuance must remain disabled without an authenticated Auth0 session");
 console.log("AUTH0 SIGNED-RECEIPT GATE FAILS CLOSED PASS");


 const mainVoice=page.getByRole("button",{name:/ENABLE SPOKEN REPLIES/i});
 assert.ok(await mainVoice.isVisible());
 await page.setViewportSize({width:390,height:844});
 await page.waitForTimeout(450);
 assert.ok(await page.getByRole("heading",{name:/Just Ask Buddy/i}).isVisible());
 const overflow=await page.evaluate(()=>document.documentElement.scrollWidth - document.documentElement.clientWidth);
 assert.ok(overflow<20,"Mobile shouldn't have large horizontal overflow: "+overflow);
 console.log("MOBILE RESPONSIVE UI PASS");
 assert.deepEqual(errors,[],"Browser JavaScript errors");
 console.log("BROWSER RUNTIME ERRORS NONE");
 await page.close();
} finally {await browser.close();}
