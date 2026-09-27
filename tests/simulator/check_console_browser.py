"""Compiled UI smoke check; sample data grants no guest compatibility credit."""

from pathlib import Path
import sys
import threading

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.dev.preview import make_server
from playwright.sync_api import sync_playwright, expect


def main():
    output = ROOT / 'build/reports/console-browser'
    output.mkdir(parents=True, exist_ok=True)
    errors, external = [], []
    with make_server(ROOT / 'build/simulator-web-demo', 0) as server:
        thread = threading.Thread(target=server.serve_forever)
        thread.start()
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                try:
                    page = browser.new_page(viewport={'width': 1440, 'height': 1000})
                    page.on('pageerror', lambda error: errors.append(str(error)))
                    origin = f'http://127.0.0.1:{server.server_port}'
                    page.on('request', lambda request: external.append(request.url)
                            if not request.url.startswith((origin + '/', 'data:', 'blob:')) else None)
                    page.goto(origin)
                    expect(page.locator('#development-banner')).to_be_visible()
                    page.locator('#view-display').click()
                    page.locator('#display-connect').click()
                    field = page.get_by_label('Demo application input')
                    expect(field).to_be_visible()
                    field.fill('Guest contents survive presentation changes')
                    frame = page.locator('#display-frame')
                    expect(frame).not_to_have_class('imac-frame unframed')
                    page.screenshot(path=str(output / 'imac-light.png'))
                    page.locator('#dark-appearance').click()
                    expect(field).to_have_value('Guest contents survive presentation changes')
                    page.screenshot(path=str(output / 'imac-dark.png'))
                    toggle = page.locator('#display-frame-toggle')
                    toggle.focus()
                    page.keyboard.press('Space')
                    expect(toggle).to_have_attribute('aria-pressed', 'false')
                    expect(field).to_have_value('Guest contents survive presentation changes')
                    page.reload()
                    expect(toggle).to_have_attribute('aria-pressed', 'false')
                    expect(page.locator('html')).to_have_attribute('data-appearance', 'dark')
                    toggle.click()
                    page.set_viewport_size({'width': 390, 'height': 844})
                    page.locator('#display-connect').click()
                    expect(field).to_be_visible()
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'horizontal overflow'
                    page.screenshot(path=str(output / 'imac-narrow-dark.png'), full_page=True)
                    page.locator('#dark-appearance').click()
                    page.screenshot(path=str(output / 'imac-narrow-light.png'), full_page=True)
                    page.locator('#console-panel > summary').click()
                    messages = page.locator('#console-messages tr')
                    expect(messages).to_have_count(2)
                    page.locator('#console-pause').click()
                    page.locator('#console-search').fill('p:SampleApp m:"permission denied"')
                    expect(messages).to_have_count(1)
                    messages.first.focus()
                    page.keyboard.press('Enter')
                    expect(page.locator('#console-detail')).to_contain_text('PID: 42')
                    page.keyboard.press('Control+f')
                    expect(page.locator('#console-search')).to_be_focused()
                    page.locator('#console-search').fill('')
                    page.locator('#console-type').select_option('errors')
                    expect(messages).to_have_count(1)
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Console horizontal overflow'
                    page.screenshot(path=str(output / 'console-narrow-light.png'), full_page=True)
                    page.set_viewport_size({'width': 1440, 'height': 1000})
                    page.locator('#dark-appearance').click()
                    page.locator('#console-panel').scroll_into_view_if_needed()
                    page.screenshot(path=str(output / 'console-dark.png'))
                    page.locator('#console-clear').click()
                    expect(messages).to_have_count(0)
                    page.locator('#console-refresh').click()
                    expect(messages).to_have_count(0)
                    assert not errors, errors
                    assert not external, external
                finally:
                    browser.close()
        finally:
            server.shutdown()
            thread.join()
    print('Console browser smoke passed: appearances, frame persistence, keyboard, narrow layout, content, offline assets.')


if __name__ == '__main__':
    main()
