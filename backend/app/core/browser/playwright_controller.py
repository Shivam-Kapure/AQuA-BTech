import asyncio
from playwright.async_api import async_playwright
from loguru import logger

from app.core.url_security import validate_target_url

async def fetch_page_html(url: str) -> str:
    """
    Launch a headless chromium browser, navigate to the URL,
    wait for the network to be idle, and return the page's HTML.
    """
    validate_target_url(url)
    logger.info(f"Scraping URL: {url}")
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            # Wait for the DOM, then give the network a short chance to settle.
            # Busy sites (video, ads, analytics) never reach "networkidle", so
            # waiting for it outright would time out and lose the page.
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            try:
                await page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:
                pass

            # Extract full HTML
            html = await page.content()
            await browser.close()
            return html
    except Exception as e:
        logger.error(f"Failed to scrape {url}: {e}")
        return ""
