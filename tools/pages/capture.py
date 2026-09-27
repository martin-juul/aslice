"""Capture the existing compiled simulator UI; no guest execution is implied."""

from pathlib import Path
from playwright.sync_api import sync_playwright

destination = Path(__file__).resolve().parent / "screenshots"
destination.mkdir(exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(
        viewport={"width": 1440, "height": 1080}, device_scale_factor=1
    )
    page.goto("http://127.0.0.1:4173/static/")
    page.locator("#start").click()
    page.locator("#shell").click()
    page.locator(".xterm-screen").wait_for()
    page.evaluate("document.fonts.ready")
    page.screenshot(path=str(destination / "console-light.png"), full_page=True)
    page.locator("#dark-appearance").click()
    page.screenshot(path=str(destination / "console-dark.png"), full_page=True)
    browser.close()
