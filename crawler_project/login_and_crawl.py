"""
苏宁易购登录并保存Cookie
登录后使用Cookie爬取需要登录的数据
"""
import json
import time
from playwright.sync_api import sync_playwright
from config import CRAWLER_CONFIG


def login_and_save_cookie():
    """
    打开浏览器让用户登录，登录成功后保存Cookie
    """
    print("=" * 60)
    print("Suning Login Tool")
    print("=" * 60)
    print("\nBrowser will open. Please login to Suning manually.")
    print("Program will wait for 60 seconds for you to login...")
    print("After login, press Enter or wait for timeout.\n")

    cookies_file = "suning_cookies.json"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Non-headless mode
        context = browser.new_context(
            viewport={'width': 1280, 'height': 720},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='zh-CN',
        )

        # Visit Suning homepage
        page = context.new_page()
        page.goto("https://www.suning.com/", timeout=60000)
        print(f"Opened: {page.url}")

        # Wait for user to login (60 seconds)
        print("\nPlease login within 60 seconds...")
        try:
            page.wait_for_timeout(60000)  # Wait 60 seconds
        except:
            pass

        # Check if user is logged in by looking at the page
        current_url = page.url
        print(f"\nCurrent URL: {current_url}")

        if 'login' not in current_url.lower():
            print("[OK] Appears to be logged in!")
        else:
            print("[INFO] Please check if login was successful")

        # Save Cookie
        cookies = context.cookies()
        with open(cookies_file, 'w', encoding='utf-8') as f:
            json.dump(cookies, f, ensure_ascii=False, indent=2)

        print(f"\n[OK] Cookie saved to: {cookies_file}")
        print(f"Total cookies: {len(cookies)}")

        browser.close()

    return cookies_file


def load_cookie():
    """加载保存的Cookie"""
    cookies_file = "suning_cookies.json"
    try:
        with open(cookies_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def test_logged_in_crawler():
    """
    使用登录后的Cookie测试爬虫
    """
    print("\n" + "=" * 60)
    print("测试登录后的爬虫")
    print("=" * 60)

    cookies = load_cookie()
    if not cookies:
        print("[ERROR] 未找到Cookie，请先登录")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='zh-CN',
        )

        # 添加Cookie
        context.add_cookies(cookies)

        page = context.new_page()

        # 测试访问商品详情页
        url = "https://product.suning.com/0010328832/12430685442.html"
        print(f"\n[TEST] 访问: {url}")

        response = page.goto(url, timeout=60000)
        print(f"[TEST] 状态: {response.status}")
        print(f"[TEST] 最终URL: {page.url}")

        # 检查是否还在登录页
        if 'login' in page.url.lower() or 'passport' in page.url.lower():
            print("[WARNING] 仍然跳转到登录页，可能是Cookie过期")
        else:
            print("[OK] 成功访问商品详情页！")

            # 获取价格
            page.wait_for_timeout(2000)  # 等待JS加载
            content = page.content()

            from bs4 import BeautifulSoup
            import re

            soup = BeautifulSoup(content, 'html.parser')

            # 查找价格
            price_spans = soup.find_all('span', class_='price')
            print(f"\n价格元素: {len(price_spans)}")
            for ps in price_spans:
                text = ps.get_text(strip=True)
                if text and text != '¥':
                    print(f"  价格: {text}")

        browser.close()


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        test_logged_in_crawler()
    else:
        login_and_save_cookie()
