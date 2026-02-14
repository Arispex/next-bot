from __future__ import annotations

from pathlib import Path


class RenderScreenshotError(Exception):
    pass


async def screenshot_url(url: str, output_path: Path) -> None:
    try:
        from playwright.async_api import async_playwright
    except Exception as exc:  # pragma: no cover
        raise RenderScreenshotError(
            "未安装 playwright，请先执行：uv add playwright && uv run playwright install chromium"
        ) from exc

    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            page = await browser.new_page(viewport={"width": 2200, "height": 1000})
            await page.goto(url, wait_until="networkidle", timeout=15000)
            await page.screenshot(path=str(output_path), full_page=True)
            await browser.close()
    except Exception as exc:
        raise RenderScreenshotError(f"截图失败：{exc}") from exc
