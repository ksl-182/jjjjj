"""
scrapers/dispatcher.py
统一入口：根据 site 参数调用对应的网站 scraper。
page 由外部（server.py 的 workflow_run）统一管理，整个流程共用一个浏览器。
"""

from playwright.sync_api import Page
from scrapers.deepseek import ask as ask_deepseek
from scrapers.chatgpt  import ask as ask_chatgpt
from scrapers.claude   import ask as ask_claude

SITE_MAP = {
    "deepseek": ask_deepseek,
    "chatgpt":  ask_chatgpt,
    "claude":   ask_claude,
}

def ask(page: Page, site: str, prompt: str) -> str:
    fn = SITE_MAP.get(site)
    if not fn:
        raise ValueError(f"未知网站：{site}，可选：{list(SITE_MAP.keys())}")
    return fn(page=page, prompt=prompt)
