from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from config import HEADLESS, TIMEOUT


async def create_browser() -> tuple[Browser, BrowserContext]:
    playwright = await async_playwright().start()

    browser = await playwright.chromium.launch(
        headless=HEADLESS,
        args=[
            "--no-sandbox",
            "--disable-blink-features=AutomationControlled",
        ],
    )

    context = await browser.new_context(
        viewport={"width": 1920, "height": 1080},
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        locale="en-US",
        extra_http_headers={
            "Accept-Language": "en-US,en;q=0.9",
        }
    )

    # Paslepiame kad tai Playwright (anti-bot)
    await context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
    """)

    context.set_default_timeout(TIMEOUT)
    return browser, context


async def new_page(context: BrowserContext) -> Page:
    page = await context.new_page()
    return page
