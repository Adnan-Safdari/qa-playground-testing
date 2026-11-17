"""Full-page screenshots for failed tests."""

from __future__ import annotations

import base64
from pathlib import Path

from selenium.webdriver.remote.webdriver import WebDriver


def capture_full_page_png(driver: WebDriver) -> bytes:
    """Return a PNG of the whole page (beyond the viewport) when the browser allows it.

    Chrome exposes this via the DevTools protocol; other browsers fall back to a
    viewport screenshot.
    """
    try:
        metrics = driver.execute_cdp_cmd("Page.getLayoutMetrics", {})
        size = metrics.get("cssContentSize") or metrics["contentSize"]
        shot = driver.execute_cdp_cmd(
            "Page.captureScreenshot",
            {
                "format": "png",
                "captureBeyondViewport": True,
                "clip": {
                    "x": 0,
                    "y": 0,
                    "width": size["width"],
                    "height": size["height"],
                    "scale": 1,
                },
            },
        )
        return base64.b64decode(shot["data"])
    except Exception:
        return driver.get_screenshot_as_png()


def save_screenshot(driver: WebDriver, path: Path) -> bytes:
    png = capture_full_page_png(driver)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png)
    return png
