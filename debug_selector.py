#!/usr/bin/env python3
"""
debug_selector.py
当某个网站的选择器失效时，用这个工具快速调试。

用法：
    python debug_selector.py deepseek
    python debug_selector.py chatgpt
    python debug_selector.py claude

会用 Profile 2 打开浏览器（有界面），按 Enter 后打印
页面上所有输入框和消息容器的 class/id 信息。
"""

import sys
from scrapers.base import launch_edge

URLS = {
    "deepseek": "https://chat.deepseek.com/",
    "chatgpt":  "https://chatgpt.com/",
    "claude":   "https://claude.ai/new",
}

def debug(site: str):
    url = URLS.get(site)
    if not url:
        print(f"未知网站：{site}，可选：{list(URLS.keys())}")
        sys.exit(1)

    pw, ctx = launch_edge(headless=False)
    page = ctx.new_page()
    page.goto(url, wait_until="networkidle", timeout=30000)

    print(f"\n已用 Profile 2 打开 {url}")
    input(">>> 页面加载完成后按 Enter 打印选择器信息...")

    print("\n=== textarea ===")
    for el in page.locator("textarea").all():
        print(" ", el.get_attribute("id"), el.get_attribute("class"), el.get_attribute("placeholder"))

    print("\n=== contenteditable ===")
    for el in page.locator('[contenteditable="true"]').all():
        print(" ", el.get_attribute("class"), el.get_attribute("data-id"), el.get_attribute("aria-label"))

    print("\n=== buttons ===")
    for el in page.locator("button").all():
        print(" ", el.get_attribute("type"), el.get_attribute("aria-label"), el.get_attribute("data-testid"))

    print("\n=== 最后5个消息容器 ===")
    for sel in ['[class*="message"]', '[class*="markdown"]', '[class*="response"]']:
        els = page.locator(sel).all()
        if els:
            print(f"  {sel} → {len(els)} 个，最后一个文本前100字：")
            print("  ", els[-1].inner_text()[:100])

    input("\n>>> 按 Enter 关闭浏览器...")
    ctx.close()
    pw.stop()

if __name__ == "__main__":
    site = sys.argv[1] if len(sys.argv) > 1 else "chatgpt"
    debug(site)
