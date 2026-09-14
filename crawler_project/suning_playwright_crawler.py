"""
苏宁易购爬虫 - Playwright版本
使用登录后的Cookie获取数据
"""
import re
import time
import json
from datetime import datetime
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

from snowflake import generate_id
from db_helper import DatabaseHelper
from minio_uploader import MinIOUploader


class SuningPlaywrightCrawler:
    """苏宁易购爬虫 - Playwright版本"""

    def __init__(self, cookies_file='suning_cookies.json'):
        self.cookies_file = cookies_file
        self.browser = None
        self.context = None
        self.page = None

    def _init_browser(self):
        """初始化浏览器"""
        if self.browser is not None:
            return

        p = sync_playwright().start()
        self.browser = p.chromium.launch(headless=True)
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

    def close(self):
        """关闭浏览器"""
        if self.browser:
            self.browser.close()
            self.browser.context = None
            self.page = None
            self.browser = None

    def search_products(self, keyword, page_num=1):
        """
        搜索商品
        """
        self._init_browser()

        url = f"https://search.suning.com/{keyword}/"
        if page_num > 1:
            url = f"https://search.suning.com/{keyword}/0/{page_num-1}.html"

        print(f"[Crawler] 搜索: {keyword} 第{page_num}页")

        try:
            self.page.goto(url, timeout=60000)
            self.page.wait_for_timeout(2000)

            html = self.page.content()
            return self._parse_search_page(html)

        except Exception as e:
            print(f"[Crawler] 请求异常: {e}")
            return []

    def _parse_search_page(self, html):
        """解析搜索结果页面"""
        products = []
        soup = BeautifulSoup(html, 'html.parser')
        product_boxes = soup.select('div.product-box')

        for box in product_boxes:
            try:
                product = {}

                # 商品名称
                img_elem = box.select_one('img')
                if img_elem:
                    product['pname'] = img_elem.get('alt', '').strip()
                else:
                    continue

                # 商品链接
                links = box.select('a[href*="product.suning.com"]')
                if links:
                    product['detail_url'] = 'https:' + links[0].get('href', '').split('#')[0]
                else:
                    continue

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
                match = re.search(r'/(\d+)\.html', product.get('detail_url', ''))
                product['goods_id'] = match.group(1) if match else ''

                products.append(product)

            except Exception as e:
                continue

        return products

    def get_product_detail(self, url):
        """
        获取商品详情
        """
        self._init_browser()

        detail_info = {}

        try:
            self.page.goto(url, timeout=60000)
            self.page.wait_for_timeout(3000)

            content = self.page.content()
            soup = BeautifulSoup(content, 'html.parser')

            # 价格
            price_spans = soup.find_all('span', class_='price')
            prices = []
            for ps in price_spans:
                text = ps.get_text(strip=True)
                if '¥' in text and re.search(r'\d', text):
                    price_match = re.search(r'[\d.]+', text)
                    if price_match:
                        try:
                            p = float(price_match.group())
                            if p > 0 and p < 1000:
                                prices.append(p)
                        except:
                            pass

            if prices:
                # 取最小且非38的价格
                valid_prices = [p for p in prices if p != 38.0]
                if valid_prices:
                    detail_info['price'] = min(valid_prices)
                else:
                    detail_info['price'] = min(prices)
            else:
                detail_info['price'] = 0.0

            # 商品参数
            param_elem = soup.select_one('[class*="param"]')
            param_text = ''
            if param_elem:
                param_text = param_elem.get_text(strip=True)

                weight_match = re.search(r'净含量[：:]*(\d+[gGmlLmM克毫升级]+)', param_text)
                if weight_match:
                    detail_info['weight'] = weight_match.group(1)
                else:
                    detail_info['weight'] = '500g'

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

            # 商品介绍 - 简洁格式：品牌-类别-口味-包装
            intro_parts = []
            if '品牌：' in param_text:
                brand_match = re.search(r'品牌[：:]*(.*?)[国产进口产地]', param_text)
                if brand_match:
                    brand = brand_match.group(1).strip()
                    if brand:
                        intro_parts.append(brand)
            if '类别：' in param_text:
                category_match = re.search(r'类别[：:]*(.*?)[国产进口]', param_text)
                if category_match:
                    category = category_match.group(1).strip()
                    if category:
                        intro_parts.append(category)
            if '口味：' in param_text:
                taste_match = re.search(r'口味[：:]*(.*?)[是否添加糖]', param_text)
                if taste_match:
                    taste = taste_match.group(1).strip()
                    if taste:
                        intro_parts.append(taste)
            if '包装：' in param_text:
                pack_match = re.search(r'包装[：:]*(.*?)[保质期]', param_text)
                if pack_match:
                    pack = pack_match.group(1).strip()
                    if pack:
                        intro_parts.append(pack)

            if intro_parts:
                detail_info['intro'] = '-'.join(intro_parts)[:200]
            else:
                detail_info['intro'] = '优质商品'

            # 详细描述 - 清理后的参数信息
            if param_text:
                # 去重：把重复的信息简化
                lines = []
                for line in param_text.split('：'):
                    line = line.replace('\n', '').strip()
                    if line and line not in lines and len(line) < 50:
                        lines.append(line)
                detail_info['detail'] = '，'.join(lines[:20])[:2000]
            else:
                detail_info['detail'] = '商品详情'

        except Exception as e:
            print(f"[Crawler] 获取详情异常: {e}")

        return detail_info

    def search_all_pages(self, keyword, max_pages=5):
        """搜索多页"""
        all_products = []

        for page in range(1, max_pages + 1):
            products = self.search_products(keyword, page)
            if not products:
                break

            all_products.extend(products)
            print(f"[Crawler] {keyword} 第{page}页: 获取 {len(products)} 个商品")

            if page < max_pages:
                time.sleep(1)

        return all_products


def crawl_category(keyword, tno, max_pages=3):
    """爬取一个分类"""
    crawler = SuningPlaywrightCrawler()
    db = DatabaseHelper()
    minio = MinIOUploader()

    db.connect()
    minio.connect()

    count = 0
    all_products = crawler.search_all_pages(keyword, max_pages)

    print(f"[INFO] {keyword} 共获取 {len(all_products)} 个商品")

    for product in all_products:
        count += 1

        # 获取详情
        detail = crawler.get_product_detail(product['detail_url'])
        product.update(detail)

        # 下载图片
        image_url = product.get('image_url', '')
        pno = generate_id()
        if image_url:
            object_name = f"goods_files/{pno}.jpg"
            image_path = minio.upload_image(image_url, object_name)
        else:
            image_path = ''

        # 构建数据
        product_data = {
            'pno': pno,
            'tno': int(tno),
            'pname': product.get('pname', '')[:50],
            'price': product.get('price', 0.0),
            'pics': image_path,
            'intro': product.get('intro', '优质商品')[:200],
            'store': 100,
            'weight': product.get('weight', '500g'),
            'unit': product.get('unit', '袋'),
            'detail': product.get('intro', '')[:2000],
            'pdate': datetime.now(),
            'status': 1
        }

        # 写入数据库
        if db.insert_product(product_data):
            print(f"[OK] #{count:03d} {product_data['pname'][:25]}... | ¥{product_data['price']}")

        time.sleep(0.5)

    crawler.close()
    db.close()

    print(f"[INFO] {keyword} 完成: {count} 条")
    return count


def main():
    """主函数"""
    print("=" * 60)
    print("苏宁易购爬虫 - Playwright版")
    print("=" * 60)

    categories = [
        ('零食', '2083190223734308864', '薯片'),
        ('饮料', '2083190855883030528', '饮料'),
        ('水果', '2083190999957372928', '水果'),
        ('糖果巧克力', '2083810791223459840', '糖果巧克力'),
        ('生活用品', '2087704651808899072', '生活用品'),
        ('服装', '2088620594038833152', '服装'),
    ]

    total = 0
    for cat_name, tno, keyword in categories:
        print(f"\n{'='*50}")
        print(f"开始爬取: {cat_name}")
        print(f"{'='*50}")
        count = crawl_category(keyword, tno, max_pages=3)
        total += count

    print(f"\n{'='*60}")
    print(f"爬取完成! 总共 {total} 条商品")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
