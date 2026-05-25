"""
scrapers/chatgpt.py
ChatGPT（chatgpt.com）
"""

from playwright.sync_api import Page
from scrapers.base import type_prompt, wait_for_response_stable

URL = "https://chatgpt.com/"

INPUT_SEL    = '#prompt-textarea, div[contenteditable="true"][data-id]'
RESPONSE_SEL = '[data-message-author-role="assistant"] .markdown'
SEND_BTN_SEL = 'button[data-testid="send-button"]'


def ask(page: Page, prompt: str) -> str:
    page.goto(URL, wait_until="networkidle", timeout=30000)
    page.wait_for_selector(INPUT_SEL, timeout=20000)

    type_prompt(page, INPUT_SEL, prompt)

    try:
        page.locator(SEND_BTN_SEL).first.click(timeout=3000)
    except Exception:
        page.locator(INPUT_SEL).first.press("Enter")

    return wait_for_response_stable(page, RESPONSE_SEL) or "（ChatGPT 未返回内容，请检查选择器）"
