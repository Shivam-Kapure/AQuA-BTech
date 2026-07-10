import asyncio
from playwright.async_api import async_playwright
from loguru import logger

async def fetch_page_html(url: str) -> str:
    """
    Launch a headless chromium browser, navigate to the URL,
    wait for the network to be idle, and return the page's HTML.
    """
    logger.info(f"Scraping URL: {url}")
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            # Navigate and wait for network/dom to settle
            await page.goto(url, wait_until="networkidle", timeout=30000)
            
            # Extract full HTML
            html = await page.content()
            await browser.close()
            return html
    except Exception as e:
        logger.error(f"Failed to scrape {url}: {e}")
        return ""
