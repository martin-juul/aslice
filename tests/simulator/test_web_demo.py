"""Standalone browser UX checks; no simulator or guest processes are involved."""

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
import re
from pathlib import Path
from threading import Thread
import unittest

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "build/simulator-web-demo"


class DemoHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB), **kwargs)

    def do_GET(self):
        if not self.path.startswith("/static/"):
            self.send_error(404)
            return
        self.path = self.path.removeprefix("/static")
        super().do_GET()

    def log_message(self, *_args):
        pass


@unittest.skipUnless(importlib.util.find_spec("playwright"), "Playwright unavailable")
class DemoConsoleTests(unittest.TestCase):
    def setUp(self):
        if not (WEB / "index.html").is_file():
            self.skipTest("run npm run build:demo in tools/simulator/web")
        server = ThreadingHTTPServer(("127.0.0.1", 0), DemoHandler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(thread.join)
        self.addCleanup(server.shutdown)
        self.origin = f"http://127.0.0.1:{server.server_port}"

    def test_terminal_samples_and_session_reset_without_controller(self):
        from playwright.sync_api import sync_playwright, expect

        origin = self.origin
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page()
            errors = []
            forbidden_requests = []
            page.on("pageerror", lambda error: errors.append(str(error)))

            def require_local_assets(route):
                if route.request.url.startswith(origin + "/static/"):
                    route.continue_()
                else:
                    forbidden_requests.append(route.request.url)
                    route.abort()

            page.route("**/*", require_local_assets)
            page.goto(origin + "/static/")
            expect(page.locator("#notice")).to_contain_text("Demo UI ready")
            page.get_by_text("Terminal options", exact=True).click()
            page.locator("#terminal-webgl").uncheck()
            page.locator("#terminal-images").check()
            expect(page.locator("#terminal-image-status")).to_contain_text("enabled")
            page.locator("#start").click()
            page.locator("#shell").click()
            expect(page.locator("#session-status")).to_have_text("Output connected.")
            page.get_by_text("Demo terminal samples", exact=True).click()
            page.locator("[data-sample=unicode]").click()
            expect(page.locator("#terminal")).to_contain_text("漢字")
            for sample, label in (
                ("progress", "Program reports progress: 42%"),
                ("busy", "Program reports work in progress"),
                ("paused", "Program reports paused: 42%"),
                ("error", "Program reports error: 42%"),
            ):
                page.locator(f"[data-sample={sample}]").click()
                expect(page.locator("#terminal-progress-label")).to_have_text(label)
            page.locator("[data-sample=image]").click()
            expect(page.locator("#terminal canvas")).to_be_visible()
            page.locator("[data-sample=disconnect]").click()
            expect(page.locator("#session-status")).to_contain_text("disconnected")
            page.locator("[data-sample=truncated]").click()
            page.locator("#session-reconnect").click()
            expect(page.locator("#session-status")).to_have_text("Output connected.")
            with page.expect_download() as received:
                page.locator("#terminal-export").click()
            snapshot = json.loads(
                Path(received.value.path()).read_text(encoding="utf-8")
            )
            self.assertIn("earlier captured output truncated", snapshot["data"])
            page.locator("#shell").click()
            expect(page.locator("#session-status")).to_have_text("Output connected.")
            expect(page.locator("#terminal-progress-area")).not_to_be_visible()
            expect(page.locator("#terminal")).not_to_contain_text(
                "Sample captured output"
            )
            page.locator("[data-sample=exit]").click()
            expect(page.locator("#session-status")).to_have_text(
                "Session exited with code 0."
            )
            self.assertEqual(errors, [])
            self.assertEqual(forbidden_requests, [])
            browser.close()

    def test_console_without_modern_browser_apis(self):
        from playwright.sync_api import sync_playwright, expect

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1600, "height": 1000})
            page.add_init_script(path=str(ROOT / "tests/simulator/legacy_browser.js"))
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(self.origin + "/static/")
            expect(page.locator("#notice")).to_contain_text("Demo UI ready")
            page.locator("#start").click()
            page.locator("#shell").click()
            expect(page.locator("#terminal")).to_contain_text("UI demo")
            page.locator("#terminal textarea").fill("hello")
            page.locator("#terminal textarea").press("Enter")
            expect(page.locator("#terminal")).to_contain_text("demo input received")
            page.get_by_text("Terminal options", exact=True).click()
            expect(page.locator("#terminal-renderer")).to_contain_text("unavailable")
            page.locator("#terminal-images").click()
            expect(page.locator("#terminal-image-status")).to_contain_text(
                "unavailable"
            )
            page.get_by_text("Terminal options", exact=True).click()
            divider = page.locator("#workspace-divider")
            bounds = divider.bounding_box()
            # The thin divider also accepts drags within two pixels of its edge.
            page.mouse.move(bounds["x"] + bounds["width"] + 1, bounds["y"] + 100)
            page.mouse.down()
            page.mouse.move(1050, bounds["y"] + 100, steps=5)
            page.mouse.up()
            self.assertGreater(int(divider.get_attribute("aria-valuenow")), 60)
            page.locator("#dark-appearance").click()
            expect(page.locator("html")).to_have_attribute("data-appearance", "dark")
            page.locator("#terminal-export").click()
            expect(page.locator("#download-ready a")).to_have_attribute(
                "href", re.compile("^blob:")
            )
            page.get_by_text("Inspectors, files & timeline", exact=True).click()
            page.locator("#file").set_input_files(
                {
                    "name": "probe.txt",
                    "mimeType": "text/plain",
                    "buffer": b"legacy transfer",
                }
            )
            page.locator("#transfer-path").fill("probe.txt")
            page.locator("#import").click()
            expect(page.locator("#notice")).to_contain_text("verified hash")
            page.locator("#export").click()
            expect(page.locator("#download-ready a")).to_have_text("Open probe.txt")
            self.assertEqual(
                page.evaluate("""() => {
                const target = document.createElement('span');
                const controller = new AbortController();
                let count = 0;
                target.addEventListener('test', () => count++, { signal: controller.signal });
                controller.abort();
                target.dispatchEvent(new Event('test'));
                target.addEventListener('test', () => count++, { once: true });
                target.dispatchEvent(new Event('test'));
                target.dispatchEvent(new Event('test'));
                return count;
            }"""),
                1,
            )
            self.assertEqual(errors, [])
            browser.close()

    def test_appearance_is_explicit_and_preserves_content(self):
        from playwright.sync_api import sync_playwright, expect

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(
                viewport={"width": 1600, "height": 1000}, color_scheme="dark"
            )
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(self.origin + "/static/")
            expect(page.locator("#notice")).to_contain_text("Demo UI ready")
            toggle = page.get_by_role("button", name="Dark appearance")
            expect(toggle).to_have_attribute("aria-pressed", "false")
            expect(page.locator("html")).to_have_attribute("data-appearance", "light")
            expect(page.locator("#terminal")).to_have_css(
                "background-color", "rgb(255, 255, 255)"
            )
            page.get_by_text("Terminal options", exact=True).click()
            page.locator("#terminal-webgl").uncheck()
            page.get_by_text("Terminal options", exact=True).click()
            page.locator("#start").click()
            page.locator("#shell").click()
            page.locator("#display-connect").click()
            session = page.locator("#sessions").input_value()
            field = page.get_by_role("textbox", name="Demo application input")
            field.fill("Preserved through appearance changes")
            for appearance, background in (
                ("dark", "rgb(30, 30, 30)"),
                ("light", "rgb(255, 255, 255)"),
            ):
                toggle.click()
                expect(page.locator("html")).to_have_attribute(
                    "data-appearance", appearance
                )
                expect(page.locator("#terminal")).to_have_css(
                    "background-color", background
                )
                expect(page.locator("#terminal .xterm-scrollable-element")).to_have_css(
                    "background-color", background
                )
                expect(page.locator("#terminal")).to_contain_text("UI demo")
                expect(field).to_have_value("Preserved through appearance changes")
                expect(field).to_have_css("background-color", "rgb(255, 255, 255)")
                self.assertEqual(page.locator("#sessions").input_value(), session)
                page.emulate_media(
                    color_scheme="light" if appearance == "dark" else "dark"
                )
                expect(page.locator("html")).to_have_attribute(
                    "data-appearance", appearance
                )
            toggle.click()
            page.reload()
            expect(toggle).to_have_attribute("aria-pressed", "true")
            page.set_viewport_size({"width": 390, "height": 844})
            self.assertEqual(page.evaluate("document.documentElement.scrollWidth"), 390)
            expect(toggle).to_be_visible()
            toggle.click()
            page.reload()
            expect(toggle).to_have_attribute("aria-pressed", "false")
            self.assertEqual(errors, [])
            browser.close()

    def test_split_resize_keyboard_drag_and_preferences(self):
        from playwright.sync_api import sync_playwright, expect

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1600, "height": 1000})
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(self.origin + "/static/")
            expect(page.locator("#notice")).to_contain_text("Demo UI ready")
            page.locator("#start").click()
            page.locator("#shell").click()
            session = page.locator("#sessions").input_value()
            divider = page.get_by_role("separator", name="Terminal width")
            divider.focus()
            divider.press("ArrowRight")
            expect(divider).to_have_attribute("aria-valuenow", "51")
            divider.press("Shift+ArrowLeft")
            expect(divider).to_have_attribute("aria-valuenow", "46")
            divider.press("Home")
            divider.press("ArrowLeft")
            expect(divider).to_have_attribute("aria-valuenow", "30")
            divider.press("End")
            divider.press("ArrowRight")
            expect(divider).to_have_attribute("aria-valuenow", "70")
            divider.press("Enter")
            expect(divider).to_have_attribute("aria-valuenow", "50")

            bounds = divider.bounding_box()
            page.mouse.move(bounds["x"] + bounds["width"] / 2, bounds["y"] + 100)
            page.mouse.down()
            page.mouse.move(1050, bounds["y"] + 100, steps=5)
            self.assertGreater(int(divider.get_attribute("aria-valuenow")), 60)
            page.keyboard.press("Escape")
            page.mouse.up()
            expect(divider).to_have_attribute("aria-valuenow", "50")
            expect(page.locator("#primary-panels")).not_to_have_class(
                "panels primary-panels resizing"
            )

            page.mouse.move(bounds["x"] + bounds["width"] / 2, bounds["y"] + 100)
            page.mouse.down()
            page.mouse.move(1050, bounds["y"] + 100, steps=5)
            page.mouse.up()
            saved = divider.get_attribute("aria-valuenow")
            self.assertGreater(int(saved), 60)
            self.assertGreater(page.locator("#terminal").bounding_box()["width"], 1000)
            self.assertEqual(page.locator("#sessions").input_value(), session)
            expect(page.locator("#session-status")).to_have_text("Output connected.")
            page.locator("#view-display").click()
            expect(divider).not_to_be_visible()
            page.locator("#view-split").click()
            expect(divider).to_have_attribute("aria-valuenow", saved)
            page.reload()
            expect(divider).to_have_attribute("aria-valuenow", saved)
            page.set_viewport_size({"width": 390, "height": 844})
            expect(divider).not_to_be_visible()
            self.assertEqual(page.evaluate("document.documentElement.scrollWidth"), 390)
            page.set_viewport_size({"width": 1600, "height": 1000})
            expect(divider).to_be_visible()
            expect(divider).to_have_attribute("aria-valuenow", saved)

            page.evaluate(
                "localStorage.setItem('aslice.workspace.split.v1', 'Infinity')"
            )
            page.reload()
            expect(divider).to_have_attribute("aria-valuenow", "50")
            page.add_init_script("""Object.defineProperty(window, 'localStorage', {
                get() { throw new DOMException('Storage disabled', 'SecurityError'); }
            });""")
            page.reload()
            expect(page.locator("#notice")).to_contain_text("Demo UI ready")
            divider.press("ArrowRight")
            expect(divider).to_have_attribute("aria-valuenow", "51")
            self.assertEqual(errors, [])
            browser.close()

    def test_workspace_selector_keyboard_and_saved_view(self):
        from playwright.sync_api import sync_playwright, expect

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.goto(self.origin + "/static/")
            expect(page.locator("#notice")).to_contain_text("Demo UI ready")
            widths = [
                page.locator(f"#view-{view}").bounding_box()["width"]
                for view in ("split", "terminal", "display")
            ]
            self.assertLess(max(widths) - min(widths), 1)
            page.locator("#view-split").focus()
            page.keyboard.press("ArrowRight")
            expect(page.locator("#view-terminal")).to_be_focused()
            expect(page.locator("#display-panel")).not_to_be_visible()
            page.keyboard.press("End")
            expect(page.locator("#view-display")).to_be_focused()
            expect(page.locator("#terminal-panel")).not_to_be_visible()
            page.reload()
            expect(page.locator("#workspace")).to_have_attribute("data-view", "display")
            expect(page.locator("#view-display")).to_have_attribute("tabindex", "0")
            page.locator("#view-display").focus()
            page.keyboard.press("Home")
            expect(page.locator("#view-split")).to_be_focused()
            expect(page.locator("#terminal-panel")).to_be_visible()
            expect(page.locator("#display-panel")).to_be_visible()
            browser.close()

    def test_workspace_views_preserve_sessions_and_fit_small_screens(self):
        from playwright.sync_api import sync_playwright, expect

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1600, "height": 1000})
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(self.origin + "/static/")
            expect(page.locator("#notice")).to_contain_text("Demo UI ready")
            page.locator("#start").click()
            page.locator("#shell").click()
            page.locator("#display-connect").click()
            session = page.locator("#sessions").input_value()
            field = page.get_by_role("textbox", name="Demo application input")
            field.fill("Preserve application state")
            page.evaluate("document.fonts.ready")
            loaded_fonts = page.evaluate("""() => [...document.fonts]
                    .filter(font => font.status === 'loaded')
                    .map(font => font.family)""")
            self.assertTrue(
                {"Geist", "Geist Mono", "Space Grotesk"} <= set(loaded_fonts)
            )
            terminal = page.locator("#terminal")
            display = page.locator("#display")
            frame = page.locator("#display-frame")
            frame_toggle = page.locator("#display-frame-toggle")
            terminal_box = terminal.bounding_box()
            display_box = display.bounding_box()
            self.assertGreater(terminal_box["height"], 600)
            # The optional hardware frame includes a bezel and chin. Check the
            # workspace allocation separately from the usable application area.
            expect(frame_toggle).to_have_attribute("aria-pressed", "true")
            self.assertGreater(frame.bounding_box()["height"], 600)
            self.assertGreater(
                display_box["height"], frame.bounding_box()["height"] * 0.8
            )
            self.assertGreater(display_box["x"], terminal_box["x"])
            frame_toggle.click()
            expect(frame_toggle).to_have_attribute("aria-pressed", "false")
            self.assertGreater(display.bounding_box()["height"], 600)
            self.assertGreater(display.bounding_box()["height"], display_box["height"])
            expect(field).to_have_value("Preserve application state")
            frame_toggle.click()

            page.locator("#view-terminal").click()
            expect(page.locator("#display-panel")).not_to_be_visible()
            self.assertGreater(terminal.bounding_box()["width"], 1500)
            page.locator("#view-display").click()
            expect(page.locator("#terminal-panel")).not_to_be_visible()
            expect(field).to_have_value("Preserve application state")
            self.assertGreater(frame.bounding_box()["width"], 1500)
            self.assertGreater(
                display.bounding_box()["width"], frame.bounding_box()["width"] * 0.9
            )
            frame_toggle.click()
            self.assertGreater(display.bounding_box()["width"], 1500)
            expect(field).to_have_value("Preserve application state")
            frame_toggle.click()
            page.locator("#view-split").click()
            self.assertEqual(page.locator("#sessions").input_value(), session)
            expect(page.locator("#session-status")).to_have_text("Output connected.")

            configuration = page.get_by_text("Machines & configuration", exact=True)
            actions = page.get_by_text("Machine actions", exact=True)
            configuration.click()
            expect(page.locator("#refresh")).to_be_visible()
            expect(page.locator("#identity")).to_contain_text("Configuration")
            expect(page.locator("#identity")).to_contain_text("8 GiB")
            expect(page.locator("#identity")).to_contain_text("Unverified")
            technical = page.get_by_text("Technical details", exact=True)
            expect(page.locator("#identity pre")).not_to_be_visible()
            technical.click()
            expect(page.locator("#identity pre")).to_contain_text('"cli": "unverified"')
            page.locator("#refresh").click()
            expect(page.locator("#refresh")).to_be_enabled()
            expect(page.locator("#identity pre")).to_be_visible()
            technical.click()
            actions.click()
            expect(page.locator("#refresh")).not_to_be_visible()
            expect(page.locator("#force")).to_be_visible()
            page.keyboard.press("Escape")
            expect(page.locator("#force")).not_to_be_visible()
            expect(actions).to_be_focused()
            configuration.click()
            page.locator("#view-terminal").click()
            expect(page.locator("#refresh")).not_to_be_visible()
            page.locator("#view-split").click()

            for width in (1600, 1100, 700, 390):
                page.set_viewport_size({"width": width, "height": 1000})
                with self.subTest(width=width):
                    self.assertEqual(
                        page.evaluate("document.documentElement.scrollWidth"), width
                    )
                    if width >= 1100:
                        self.assertEqual(
                            page.evaluate("document.documentElement.scrollHeight"), 1000
                        )
                    else:
                        terminal_box = terminal.bounding_box()
                        display_box = display.bounding_box()
                        self.assertGreaterEqual(
                            display_box["y"], terminal_box["y"] + terminal_box["height"]
                        )
                    actions.click()
                    panel = page.locator(".machine-panel[open] .panel-content")
                    bounds = panel.bounding_box()
                    self.assertGreaterEqual(bounds["x"], 0)
                    self.assertLessEqual(bounds["x"] + bounds["width"], width)
                    page.keyboard.press("Escape")

            field.fill("Narrow-screen input")
            page.get_by_role("button", name="Apply", exact=True).click()
            expect(page.locator(".demo-window output")).to_have_text(
                "Narrow-screen input"
            )
            self.assertEqual(errors, [])
            browser.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)
