#!/usr/bin/env python3
"""
LMS Playwright Tester
run:
python3 webapp_tester.py --url https://iqralms.com --email admin@ailms.com --password Admin@123456
"""

import asyncio
import json
import time
import argparse
from urllib.parse import urljoin, urlparse
from playwright.async_api import async_playwright

# ─── CONFIG ───────────────────────────────────────────────────────────────────
MAX_PAGES_TO_DISCOVER = 20
SLOW_PAGE_THRESHOLD_MS = 3000
HEADLESS = True  # Set False to watch browser during debug
# ──────────────────────────────────────────────────────────────────────────────


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")


class LMSTester:
    def __init__(self, base_url, email, password):
        self.base_url = base_url.rstrip("/")
        self.email = email
        self.password = password
        self.discovered_pages = []
        self.results = []

    # ── HELPERS ───────────────────────────────────────────────────────────────

    def record(self, name, status, detail):
        emoji = {"passed": "✅", "failed": "❌", "warning": "⚠️"}.get(status, "•")
        log(f"{emoji} {name}: {detail}")
        self.results.append({"name": name, "status": status, "detail": detail})

    async def goto(self, page, path, wait="networkidle"):
        url = path if path.startswith("http") else urljoin(self.base_url, path)
        try:
            resp = await page.goto(url, wait_until=wait, timeout=15000)
            await page.wait_for_timeout(1000)
            return resp
        except Exception as e:
            log(f"  ⚠ goto({url}) failed: {e}")
            return None

    async def click_first(self, page, selectors):
        """Try multiple selectors, click the first match."""
        for sel in selectors:
            try:
                el = page.locator(sel).first
                if await el.count() > 0:
                    await el.click(timeout=5000)
                    return sel
            except Exception:
                continue
        return None

    async def fill_first(self, page, selectors, value):
        for sel in selectors:
            try:
                el = page.locator(sel).first
                if await el.count() > 0:
                    await el.fill(value, timeout=5000)
                    return True
            except Exception:
                continue
        return False

    # ── STEP 1: LOGIN ─────────────────────────────────────────────────────────

    async def dismiss_cookie_banner(self, page):
        """Click Accept on cookie/consent banners if present."""
        for sel in [
            "button:has-text('Accept all')",
            "button:has-text('Accept All')",
            "button:has-text('Accept')",
            "button:has-text('OK')",
            "#cookie-accept"
        ]:
            try:
                el = page.locator(sel).first
                if await el.count() > 0:
                    await el.click(timeout=3000)
                    log("  ✓ Cookie banner dismissed")
                    await page.wait_for_timeout(500)
                    return
            except Exception:
                continue

    async def login(self, page):
        log("→ Logging in...")
        await self.goto(page, "/en/auth/login", wait="domcontentloaded")
        await page.wait_for_timeout(3000)  # wait for JS to render

        # Dismiss cookie banner first
        await self.dismiss_cookie_banner(page)

        # Fill email — use exact IDs found from debug
        email_filled = await self.fill_first(page, [
            "#login-email",
            "input[type='email']",
            "input[name='email']",
            "#email", "#username"
        ], self.email)

        # Fill password
        pass_filled = await self.fill_first(page, [
            "#login-password",
            "input[type='password']",
            "input[name='password']",
            "#password"
        ], self.password)

        if not email_filled or not pass_filled:
            self.record("Login", "failed", "Could not find email/password fields")
            return False

        # Submit — target the Sign In button specifically
        clicked = await self.click_first(page, [
            "button:has-text('Sign In')",
            "button:has-text('Login')",
            "button:has-text('Sign in')",
            "button.btn-primary",
            "button[type='submit']",
        ])

        if not clicked:
            self.record("Login", "failed", "Submit button not found")
            return False

        await page.wait_for_timeout(4000)
        current = page.url

        if "/login" in current or "/auth" in current:
            self.record("Login", "failed", f"Still on login page: {current}")
            return False

        self.record("Login", "passed", f"Redirected to {current}")
        return True

    # ── STEP 2: DISCOVER PAGES ────────────────────────────────────────────────

    async def discover_pages(self, page):
        log("→ Discovering internal pages...")
        await self.goto(page, "/")
        await page.wait_for_timeout(1000)

        links = await page.evaluate("""
            () => Array.from(document.querySelectorAll('a[href]'))
                .map(a => a.href)
                .filter(h => h.startsWith(window.location.origin))
        """)

        seen = set()
        domain = urlparse(self.base_url).netloc

        for link in links:
            parsed = urlparse(link)
            if parsed.netloc == domain and link not in seen:
                seen.add(link)
                self.discovered_pages.append(link)
            if len(self.discovered_pages) >= MAX_PAGES_TO_DISCOVER:
                break

        log(f"  Found {len(self.discovered_pages)} pages")

    # ── STEP 3: FUNCTIONAL TESTS ──────────────────────────────────────────────

    async def test_page_loads(self, page):
        """Check all discovered pages load without errors."""
        log("→ Testing page loads...")
        for url in self.discovered_pages:
            try:
                start = time.time()
                resp = await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                ms = round((time.time() - start) * 1000)
                status = resp.status if resp else 0
                path = urlparse(url).path or "/"

                if status >= 400:
                    self.record(f"Page Load: {path}", "failed", f"HTTP {status} in {ms}ms")
                elif ms > SLOW_PAGE_THRESHOLD_MS:
                    self.record(f"Page Load: {path}", "warning", f"Slow: {ms}ms")
                else:
                    self.record(f"Page Load: {path}", "passed", f"{status} in {ms}ms")
            except Exception as e:
                self.record(f"Page Load: {url}", "failed", str(e))

    async def test_login_page(self, page):
        log("→ Testing login page elements...")
        await self.goto(page, "/en/auth/login", wait="domcontentloaded")
        await page.wait_for_timeout(3000)
        has_email = await page.locator("#login-email, input[type='email']").count() > 0
        has_pass = await page.locator("#login-password, input[type='password']").count() > 0
        has_btn = await page.locator("button:has-text('Sign In'), button.btn-primary").count() > 0

        if has_email and has_pass and has_btn:
            self.record("Login Page", "passed", "Email, password, submit all present")
        else:
            missing = [k for k, v in {"email": has_email, "password": has_pass, "submit": has_btn}.items() if not v]
            self.record("Login Page", "warning", f"Missing: {missing}")

    async def test_dashboard(self, page):
        log("→ Testing dashboard...")
        await self.goto(page, "/dashboard")
        title = await page.title()
        content = await page.content()

        if "login" in page.url.lower():
            self.record("Dashboard", "failed", "Redirected to login — session lost")
            return

        has_stats = any(k in content.lower() for k in ["enrolled", "completed", "points", "streak", "course"])
        self.record("Dashboard", "passed" if has_stats else "warning",
                    f"Title: '{title}' | Stats content: {has_stats}")

    async def test_navigation_links(self, page):
        log("→ Testing nav links...")
        await self.goto(page, "/")
        nav_links = await page.evaluate("""
            () => Array.from(document.querySelectorAll('nav a, header a'))
                .map(a => ({ text: a.innerText.trim(), href: a.href }))
                .filter(a => a.text && a.href)
        """)

        broken = 0
        for link in nav_links[:10]:
            try:
                resp = await page.goto(link["href"], wait_until="domcontentloaded", timeout=10000)
                if resp and resp.status >= 400:
                    broken += 1
            except Exception:
                broken += 1

        total = min(len(nav_links), 10)
        self.record("Nav Links", "passed" if broken == 0 else "warning",
                    f"{total - broken}/{total} links OK")

    async def test_search(self, page):
        log("→ Testing search...")
        await self.goto(page, "/")
        filled = await self.fill_first(page, [
            "input[type='search']", "input[name='search']",
            "input[placeholder*='Search' i]", ".search-input", "#search"
        ], "python")

        if not filled:
            self.record("Search", "warning", "Search input not found")
            return

        await page.keyboard.press("Enter")
        await page.wait_for_timeout(3000)
        results_count = await page.locator(".card, .result, .course-card, article").count()
        self.record("Search", "passed", f"Got {results_count} result elements")

    async def test_create_course_button(self, page):
        log("→ Testing Create Course button...")
        await self.goto(page, "/dashboard")
        clicked = await self.click_first(page, [
            "button:has-text('Create Course')",
            "a:has-text('Create Course')",
            "[href*='create']",
        ])

        if not clicked:
            self.record("Create Course Button", "warning", "Button not found")
            return

        await page.wait_for_timeout(2000)
        has_form = await page.locator("form, input[name='title'], #title").count() > 0
        self.record("Create Course Button", "passed" if has_form else "warning",
                    "Form opened" if has_form else "Clicked but no form detected")

    async def test_notifications(self, page):
        log("→ Testing notifications...")
        await self.goto(page, "/dashboard")
        clicked = await self.click_first(page, [
            ".notification-bell", "[aria-label*='notif' i]",
            "button:has-text('Notifications')", ".fa-bell", "[href*='notification']"
        ])

        if not clicked:
            self.record("Notifications", "warning", "Notification icon not found")
            return

        await page.wait_for_timeout(1500)
        panel_visible = await page.locator(
            ".notification-list, .notifications-panel, .dropdown-menu"
        ).count() > 0
        self.record("Notifications", "passed" if panel_visible else "warning",
                    "Panel opened" if panel_visible else "Clicked but no panel")

    async def test_profile_menu(self, page):
        log("→ Testing profile menu...")
        await self.goto(page, "/dashboard")
        clicked = await self.click_first(page, [
            ".profile-menu", ".user-avatar", ".user-menu",
            "[aria-label*='profile' i]", ".avatar"
        ])

        if not clicked:
            self.record("Profile Menu", "warning", "Profile icon not found")
            return

        await page.wait_for_timeout(1500)
        menu_visible = await page.locator(
            ".dropdown-menu, .profile-dropdown, [role='menu']"
        ).count() > 0
        self.record("Profile Menu", "passed" if menu_visible else "warning",
                    "Menu opened" if menu_visible else "Clicked but no dropdown")

    async def test_logout(self, page):
        log("→ Testing logout...")
        await self.goto(page, "/dashboard")
        clicked = await self.click_first(page, [
            "a:has-text('Logout')", "button:has-text('Logout')",
            "a:has-text('Sign out')", "[href*='logout']", "[href*='signout']"
        ])

        if not clicked:
            # Try opening profile menu first
            await self.click_first(page, [".user-avatar", ".avatar", ".profile-menu"])
            await page.wait_for_timeout(1000)
            clicked = await self.click_first(page, [
                "a:has-text('Logout')", "button:has-text('Logout')", "[href*='logout']"
            ])

        if not clicked:
            self.record("Logout", "warning", "Logout button not found")
            return

        await page.wait_for_timeout(2000)
        on_login = "login" in page.url.lower() or "signin" in page.url.lower()
        self.record("Logout", "passed" if on_login else "warning",
                    f"Redirected to {page.url}")

    # ── STEP 4: PERFORMANCE ───────────────────────────────────────────────────

    async def test_performance(self, page):
        log("→ Testing page performance...")
        paths = ["/", "/dashboard", "/courses", "/login"]
        for path in paths:
            try:
                start = time.time()
                await page.goto(urljoin(self.base_url, path),
                                wait_until="networkidle", timeout=20000)
                ms = round((time.time() - start) * 1000)
                status = "passed" if ms < SLOW_PAGE_THRESHOLD_MS else "warning"
                self.record(f"Perf: {path}", status, f"{ms}ms")
            except Exception as e:
                self.record(f"Perf: {path}", "failed", str(e))

    # ── MAIN RUNNER ───────────────────────────────────────────────────────────

    async def run(self):
        log(f"Starting tests → {self.base_url}")
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=HEADLESS,
                args=["--no-sandbox", "--disable-dev-shm-usage"]
            )
            context = await browser.new_context(
                viewport={"width": 1280, "height": 800},
                ignore_https_errors=True
            )
            page = await context.new_page()

            # ── Run in order ──
            logged_in = await self.login(page)

            if logged_in:
                await self.discover_pages(page)
                await self.test_dashboard(page)
                await self.test_navigation_links(page)
                await self.test_search(page)
                await self.test_create_course_button(page)
                await self.test_notifications(page)
                await self.test_profile_menu(page)
                await self.test_page_loads(page)
                await self.test_performance(page)
                await self.test_logout(page)
            else:
                await self.test_login_page(page)

            await browser.close()

        # ── Summary ──
        total = len(self.results)
        passed = sum(1 for r in self.results if r["status"] == "passed")
        failed = sum(1 for r in self.results if r["status"] == "failed")
        warnings = sum(1 for r in self.results if r["status"] == "warning")

        summary = {
            "url": self.base_url,
            "total": total,
            "passed": passed,
            "failed": failed,
            "warnings": warnings,
            "pass_rate": f"{round(passed/total*100)}%" if total else "0%",
            "results": self.results
        }

        log(f"\n{'='*40}")
        log(f"Total: {total} | ✅ {passed} | ❌ {failed} | ⚠️  {warnings}")
        log(f"Pass rate: {summary['pass_rate']}")
        return summary


# ── ENTRY POINT ───────────────────────────────────────────────────────────────

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True, help="Base URL e.g. https://site.com")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--output", default="test_results.json")
    args = parser.parse_args()

    tester = LMSTester(args.url, args.email, args.password)
    summary = await tester.run()

    with open(args.output, "w") as f:
        json.dump(summary, f, indent=2)

    log(f"Results saved → {args.output}")

if __name__ == "__main__":
    asyncio.run(main())