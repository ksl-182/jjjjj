"""
scrapers/base.py
公共工具：启动 Edge、等待回复出现、提取文本
"""

import time
from pathlib import Path
from playwright.sync_api import sync_playwright, Page, BrowserContext

# ── 固定配置：始终使用 Automation 配置 ────────────────────────────────────────
EDGE_USER_DATA = str(
    Path.home() / "AppData" / "Local" / "Microsoft" / "Edge" / "User Data"
)
EDGE_PROFILE = "Automation"


def launch_edge(headless: bool = False):
    """
    启动 Playwright Edge，复用 Automation 配置的已登录 cookie。
    返回 (playwright, context)，调用方负责 ctx.close() / pw.stop()。
    """
    pw = sync_playwright().start()
    context = pw.chromium.launch_persistent_context(
        user_data_dir=EDGE_USER_DATA,
        channel="msedge",
        headless=headless,
        args=[
            "--disable-blink-features=AutomationControlled",
            f"--profile-directory={EDGE_PROFILE}",
        ],
        viewport={"width": 1280, "height": 900},
        locale="zh-CN",
    )
    return pw, context


def type_prompt(page: Page, selector: str, text: str):
    """找到输入框，清空后分段输入文本。"""
    box = page.locator(selector).first
    box.click()
    box.press("Control+a")
    box.press("Delete")
    for i in range(0, len(text), 2000):
        box.type(text[i:i + 2000], delay=10)


def wait_for_response_stable(
    page: Page,
    response_selector: str,
    stable_seconds: float = 3.0,
    timeout: float = 180.0,
    poll_interval: float = 1.5,
) -> str:
    """
    轮询最后一个 response_selector 元素的文本，
    连续 stable_seconds 不变则认为回复完成，返回文本。
    """
    deadline = time.time() + timeout
    last_text = ""
    stable_since = None

    while time.time() < deadline:
        time.sleep(poll_interval)
        els = page.locator(response_selector).all()
        if not els:
            continue
        current = els[-1].inner_text()
        if current != last_text:
            last_text = current
            stable_since = time.time()
        else:
            if stable_since and (time.time() - stable_since) >= stable_seconds:
                return current.strip()

    return last_text.strip()
