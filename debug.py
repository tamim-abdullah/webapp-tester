# Quick debug script - run this first
import asyncio
from playwright.async_api import async_playwright

async def debug():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # watch it
        page = await browser.new_page()
        await page.goto("https://iqralms.com/en/auth/login")
        await page.wait_for_timeout(4000)  # wait for JS to load
        
        # Dump all inputs found
        inputs = await page.evaluate("""
            () => Array.from(document.querySelectorAll('input')).map(i => ({
                type: i.type,
                name: i.name,
                id: i.id,
                placeholder: i.placeholder,
                className: i.className
            }))
        """)
        print("INPUTS FOUND:", inputs)
        
        buttons = await page.evaluate("""
            () => Array.from(document.querySelectorAll('button')).map(b => ({
                type: b.type,
                text: b.innerText,
                id: b.id,
                className: b.className
            }))
        """)
        print("BUTTONS FOUND:", buttons)
        
        await browser.close()

asyncio.run(debug())