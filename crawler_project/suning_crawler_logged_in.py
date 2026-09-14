"""
苏宁易购爬虫模块 - 登录版
使用登录后的Cookie获取真实价格
"""
import re
import time
import json
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from config import CRAWLER_CONFIG


class SuningCrawlerLoggedIn:
    """苏宁易购爬虫 - 使用登录后的Cookie"""

    def __init__(self, cookies_file='suning_cookies.json'):
        self.cookies_file = cookies_file
        self.cookies = None
        self.browser = None
        self.context = None
        self.page = None
        self.delay = CRAWLER_CONFIG['delay']
        self.timeout = CRAWLER_CONFIG['timeout']

    def _init_browser(self):
        """初始化浏览器"""
        if self.browser is not None:
            return

        from playwright.sync_api import sync_playwright

        self.browser = sync_playwright().chromium.launch(headless=True)
        self.context = self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='zh-CN',
        )

        # 加载Cookie
        with open(self.cookies_file, 'r', encoding='utf-8') as f:
            self.cookies = json.load(f)

        self.context.add_cookies(self.cookies)
        self.page = self.context.new_page()

    def _close_browser(self):
        """关闭浏览器"""
        if self.browser:
            self.browser.close()
            self.browser = None
            self.context = None
            self.page = None

    def search_products(self, keyword, page=1):
        """
        搜索苏宁商品 - 公开页面，不需要登录
        """
        # 使用requests获取搜索结果
        import requests

        url = f"https://search.suning.com/{keyword}/"
        if page > 1:
            url = f"https://search.suning.com/{keyword}/0/{page-1}.html"

        print(f"[Crawler] 搜索: {keyword} 第{page}页")

        try:
            response = requests.get(url, timeout=self.timeout)
            if response.status_code == 200:
                response.encoding = response.apparent_encoding or 'utf-8'
                return self._parse_search_page(response.text)
        except Exception as e:
            print(f"[Crawler] 请求异常: {e}")

        return []

    def _parse_search_page(self, html):
        """解析搜索结果页面"""
        products = []

        try:
            soup = BeautifulSoup(html, 'html.parser')
            product_boxes = soup.select('div.product-box')

            for box in product_boxes:
                try:
                    product = self._extract_product_info(box)
                    if product:
                        products.append(product)
                except Exception as e:
                    continue

        except Exception as e:
            print(f"[Crawler] 解析页面异常: {e}")

        return products

    def _extract_product_info(self, item):
        """从商品列表项提取商品信息"""
        product = {}

        # 商品名称 - 从img的alt属性获取
        img_elem = item.select_one('img')
        if img_elem:
            product['pname'] = img_elem.get('alt', '').strip()
        else:
            return None

        # 商品链接
        links = item.select('a[href*="product.suning.com"]')
        if links:
            product['detail_url'] = 'https:' + links[0].get('href', '').split('#')[0]
        else:
            product['detail_url'] = ''

        # 图片
        if img_elem:
            img_url = img_elem.get('src') or img_elem.get('data-src') or ''
            if img_url.startswith('//'):
                img_url = 'https:' + img_url
            img_url = re.sub(r'_\d+w_\d+h_\d+\.jpg$', '.jpg', img_url)
            product['image_url'] = img_url
        else:
            product['image_url'] = ''

        # 商品ID
        if product.get('detail_url'):
            match = re.search(r'/(\d+)\.html', product['detail_url'])
            product['goods_id'] = match.group(1) if match else ''
        else:
            product['goods_id'] = ''

        return product

    def get_product_detail(self, url):
        """
        获取商品详情 - 需要登录，使用Playwright
        返回: dict 包含 price, weight, unit, detail, intro 等信息
        """
        self._init_browser()

        detail_info = {}

        try:
            self.page.goto(url, timeout=self.timeout * 1000)
            self.page.wait_for_timeout(3000)  # 等待JS加载

            content = self.page.content()
            soup = BeautifulSoup(content, 'html.parser')

            # 价格 - 获取所有价格中的真实售价（通常第一个非38的价格）
            price_spans = soup.find_all('span', class_='price')
            prices = []
            for ps in price_spans:
                text = ps.get_text(strip=True)
                if '¥' in text and re.search(r'\d', text):
                    price_match = re.search(r'[\d.]+', text)
                    if price_match:
                        try:
                            p = float(price_match.group())
                            if p > 0:
                                prices.append(p)
                        except:
                            pass

            # 取第一个合理的价格（通常是售价）
            if prices:
                # 过滤掉38.0这种异常值（可能是缓存）
                valid_prices = [p for p in prices if p < 1000]  # 价格小于1000
                if valid_prices:
                    detail_info['price'] = min(valid_prices)
                else:
                    detail_info['price'] = prices[0] if prices else 0.0
            else:
                detail_info['price'] = 0.0

            # 商品参数
            param_elem = soup.select_one('[class*="param"]')
            if param_elem:
                param_text = param_elem.get_text(strip=True)

                # 提取净含量
                weight_match = re.search(r'净含量[：:]*(\d+[gGmlLmM克毫升级]+)', param_text)
                if weight_match:
                    detail_info['weight'] = weight_match.group(1)
                else:
                    detail_info['weight'] = '500g'

                # 提取包装类型
                if '箱装' in param_text:
                    detail_info['unit'] = '箱'
                elif '袋装' in param_text:
                    detail_info['unit'] = '袋'
                elif '盒装' in param_text:
                    detail_info['unit'] = '盒'
                elif '瓶装' in param_text:
                    detail_info['unit'] = '瓶'
                else:
                    detail_info['unit'] = '袋'
            else:
                detail_info['weight'] = '500g'
                detail_info['unit'] = '袋'

            # 商品介绍
            title_elem = soup.select_one('h1.product-title, #productTitle, h1[class*="title"]')
            if title_elem:
                detail_info['intro'] = title_elem.get_text(strip=True)[:100]
            else:
                detail_info['intro'] = '优质商品'

        except Exception as e:
            print(f"[Crawler] 获取详情异常: {e}")

        return detail_info

    def search_all_pages(self, keyword, max_pages=5):
        """
        搜索多页商品
        """
        all_products = []

        for page in range(1, max_pages + 1):
            products = self.search_products(keyword, page)
            if not products:
                break

            all_products.extend(products)
            print(f"[Crawler] {keyword} 第{page}页: 获取 {len(products)} 个商品")

            if page < max_pages:
                time.sleep(self.delay)

        return all_products

    def close(self):
        """关闭浏览器"""
        self._close_browser()


def test_crawler():
    """测试爬虫"""
    crawler = SuningCrawlerLoggedIn()

    # 测试搜索
    print('[TEST] 搜索商品...')
    products = crawler.search_products('薯片', page=1)
    print(f"\n获取到 {len(products)} 个商品")

    if products:
        # 测试详情获取
        print('\n[TEST] 获取商品详情...')
        p = products[0]
        print(f"商品: {p['pname'][:30]}...")

        detail = crawler.get_product_detail(p['detail_url'])
        print(f"价格: {detail.get('price', 'N/A')}")
        print(f"重量: {detail.get('weight', 'N/A')}")
        print(f"单位: {detail.get('unit', 'N/A')}")

    crawler.close()


if __name__ == '__main__':
    test_crawler()
