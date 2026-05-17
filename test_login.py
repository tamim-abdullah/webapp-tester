# save as test_login.py and run it
import asyncio
from playwright.async_api import async_playwright

async def test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        await page.goto("https://iqralms.com/en/auth/login")
        await page.wait_for_timeout(3000)
        
        # Dismiss cookie banner
        try:
            btn = page.locator("button:has-text('Accept all')")
            if await btn.count() > 0:
                await btn.click()
                print("✅ Cookie dismissed")
                await page.wait_for_timeout(1000)
        except: pass
        
        # Fill fields using exact IDs
        await page.fill("#login-email", "admin@ailms.com")
        await page.fill("#login-password", "Admin@123456")
        await page.click("button:has-text('Sign In')")
        
        await page.wait_for_timeout(4000)
        print("Current URL:", page.url)
        await browser.close()

asyncio.run(test())