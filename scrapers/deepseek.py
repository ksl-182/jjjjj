"""
scrapers/deepseek.py
DeepSeek（chat.deepseek.com）
"""

from playwright.sync_api import Page
from scrapers.base import type_prompt, wait_for_response_stable

URL = "https://chat.deepseek.com/"

INPUT_SEL    = 'textarea#chat-input, textarea[placeholder]'
RESPONSE_SEL = '.ds-markdown, [class*="markdown"], [class*="message-content"]'
SEND_BTN_SEL = 'button[aria-label="Send"], button[type="submit"]'


def ask(page: Page, prompt: str) -> str:
    page.goto(URL, wait_until="networkidle", timeout=30000)
    page.wait_for_selector(INPUT_SEL, timeout=20000)

    type_prompt(page, INPUT_SEL, prompt)

    try:
        page.locator(SEND_BTN_SEL).first.click(timeout=3000)
    except Exception:
        page.locator(INPUT_SEL).first.press("Enter")

    return wait_for_response_stable(page, RESPONSE_SEL) or "（DeepSeek 未返回内容，请检查选择器）"
