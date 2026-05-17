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

async def debug_notifications(page):
    print("\n─── NOTIFICATIONS ───")
    await page.goto(f"{BASE_URL}/en/dashboard")
    await page.wait_for_timeout(2000)
    await page.click('[aria-label="Notifications"]')
    await page.wait_for_timeout(2000)
    # Dump what appeared
    for sel in ['[role="dialog"]', '[class*="dropdown"]', '[class*="notif"]', '[class*="panel"]', '[class*="popup"]']:
        count = await page.locator(sel).count()
        if count > 0:
            text = await page.locator(sel).first.inner_text()
            print(f"  {sel} → count={count} text='{text[:60]}'")
    print(f"  URL after click: {page.url}")

async def debug_profile(page):
    print("\n─── PROFILE MENU ───")
    await page.goto(f"{BASE_URL}/en/dashboard")
    await page.wait_for_timeout(2000)
    await page.click('nav a.w-9, nav [class*="rounded-full"]')
    await page.wait_for_timeout(2000)
    for sel in ['[role="menu"]', '[role="dialog"]', '[class*="dropdown"]', '[class*="profile"]', '[class*="popup"]']:
        count = await page.locator(sel).count()
        if count > 0:
            text = await page.locator(sel).first.inner_text()
            print(f"  {sel} → count={count} text='{text[:80]}'")
    print(f"  URL after click: {page.url}")

async def debug_create_course(page):
    print("\n─── CREATE COURSE ───")
    await page.goto(f"{BASE_URL}/en/dashboard")
    await page.wait_for_timeout(2000)
    await page.click("button:has-text('Create Course'), a:has-text('Create Course')")
    await page.wait_for_timeout(3000)
    print(f"  URL after click: {page.url}")
    for sel in ['form', 'input', '[role="dialog"]', '[class*="modal"]', '[class*="drawer"]', '[class*="wizard"]']:
        count = await page.locator(sel).count()
        if count > 0:
            print(f"  {sel} → count={count}")

async def debug_logout(page):
    print("\n─── LOGOUT (via profile SA button) ───")
    await page.goto(f"{BASE_URL}/en/dashboard")
    await page.wait_for_timeout(2000)
    await page.click('nav a.w-9, nav [class*="rounded-full"]')
    await page.wait_for_timeout(2000)
    # Look for logout in whatever opened
    for sel in ["a:has-text('Logout')", "a:has-text('Sign out')", "button:has-text('Logout')", "[href*='logout']", "[href*='signout']"]:
        count = await page.locator(sel).count()
        if count > 0:
            print(f"  Found logout: {sel}")

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page(viewport={"width": 1280, "height": 800})
        await login(page)
        await debug_notifications(page)
        await debug_profile(page)
        await debug_create_course(page)
        await debug_logout(page)
        print("\n─── DONE ───")
        await browser.close()

asyncio.run(main())