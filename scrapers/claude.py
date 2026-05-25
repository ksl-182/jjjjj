"""
scrapers/claude.py
Claude.ai（claude.ai）
"""

from playwright.sync_api import Page
from scrapers.base import type_prompt, wait_for_response_stable

URL = "https://claude.ai/new"

INPUT_SEL    = 'div[contenteditable="true"].ProseMirror, div[contenteditable="true"]'
RESPONSE_SEL = '[data-is-streaming="false"] .font-claude-message, .font-claude-message'
SEND_BTN_SEL = 'button[aria-label="Send Message"], button[type="submit"]'


def ask(page: Page, prompt: str) -> str:
    page.goto(URL, wait_until="networkidle", timeout=30000)
    page.wait_for_selector(INPUT_SEL, timeout=20000)

    type_prompt(page, INPUT_SEL, prompt)

    try:
        page.locator(SEND_BTN_SEL).first.click(timeout=3000)
    except Exception:
        page.locator(INPUT_SEL).first.press("Enter")

    # Claude 回复较慢，延长稳定等待时间
    return wait_for_response_stable(
        page, RESPONSE_SEL,
        stable_seconds=4.0,
        timeout=240.0
    ) or "（Claude.ai 未返回内容，请检查选择器）"
