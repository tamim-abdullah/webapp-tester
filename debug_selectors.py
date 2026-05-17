import asyncio
from playwright.async_api import async_playwright

BASE_URL = "https://iqralms.com"
EMAIL = "admin@ailms.com"
PASSWORD = "Admin@123456"

async def login(page):
    await page.goto(f"{BASE_URL}/en/auth/login")
    await page.wait_for_timeout(3000)
    try:
        if await page.locator("button:has-text('Accept all')").count() > 0:
            await page.click("button:has-text('Accept all')")
            await page.wait_for_timeout(500)
    except: pass
    await page.fill("#login-email", EMAIL)
    await page.fill("#login-password", PASSWORD)
    await page.click("button:has-text('Sign In')")
    await page.wait_for_timeout(4000)
    print(f"Logged in → {page.url}")

async def dump_elements(page, css_selector, label):
    print(f"\n─── {label} ───")
    locator = page.locator(css_selector)
    count = await locator.count()
    print(f"Found {count} elements")
    for i in range(min(count, 20)):
        el = locator.nth(i)
        try:
            text = (await el.inner_text()).strip()[:40]
            cls = await el.get_attribute("class") or ""
            id_ = await el.get_attribute("id") or ""
            aria = await el.get_attribute("aria-label") or ""
            href = await el.get_attribute("href") or ""
            print(f"  [{i}] text='{text}' id='{id_}' class='{cls[:50]}' aria='{aria}' href='{href}'")
        except:
            print(f"  [{i}] (could not read)")

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page(viewport={"width": 1280, "height": 800})
        await login(page)

        await page.goto(f"{BASE_URL}/en/dashboard")
        await page.wait_for_timeout(2000)

        await dump_elements(page, "header button", "HEADER BUTTONS")
        await dump_elements(page, "header a", "HEADER LINKS")
        await dump_elements(page, "nav button, nav a", "NAV ELEMENTS")

        # Click first header button and see what appears
        print("\n─── CLICKING EACH HEADER BUTTON ───")
        count = await page.locator("header button").count()
        for i in range(min(count, 8)):
            await page.goto(f"{BASE_URL}/en/dashboard")
            await page.wait_for_timeout(1500)
            btn = page.locator("header button").nth(i)
            try:
                text = (await btn.inner_text()).strip()[:30]
                await btn.click()
                await page.wait_for_timeout(2000)
                # Check what appeared
                modal = await page.locator('[role="dialog"], [class*="modal"], [class*="dropdown"], [class*="panel"], [class*="drawer"]').count()
                print(f"  Button[{i}] '{text}' → url={page.url.split('/')[-1]} | overlays={modal}")
            except Exception as e:
                print(f"  Button[{i}] error: {e}")

        print("\n─── DONE ───")
        await browser.close()

asyncio.run(main())