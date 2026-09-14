"""
苏宁易购爬虫模块
反爬机制较弱，可以直接爬取
"""
import re
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from config import CRAWLER_CONFIG


class SuningCrawler:
    """苏宁易购商品爬虫"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(CRAWLER_CONFIG['headers'])
        self.delay = CRAWLER_CONFIG['delay']
        self.timeout = CRAWLER_CONFIG['timeout']

        # 更新User-Agent
        self.session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'https://www.suning.com/',
        })

    def search_products(self, keyword, page=1):
        """
        搜索苏宁商品

        keyword: 搜索关键词
        page: 页码

        返回: 商品列表
        """
        url = f"https://search.suning.com/{keyword}/"
        if page > 1:
            url = f"https://search.suning.com/{keyword}/0/{page-1}.html"

        print(f"[Crawler] 搜索: {keyword} 第{page}页")

        try:
            response = self.session.get(url, timeout=self.timeout)
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

        # 商品名称 - 从img的alt属性获取（真正的商品名称）
        img_elem = item.select_one('img')
        if img_elem:
            product['pname'] = img_elem.get('alt', '').strip()
        else:
            return None

        # 商品链接 - 查找包含product.suning.com的链接
        links = item.select('a[href*="product.suning.com"]')
        if links:
            product['detail_url'] = 'https:' + links[0].get('href', '').split('#')[0]
        else:
            product['detail_url'] = ''

        # 价格（列表页可能没有，需要从详情页获取）
        product['price'] = 0.0

        # 图片
        if img_elem:
            img_url = img_elem.get('src') or img_elem.get('data-src') or ''
            # 补全URL
            if img_url.startswith('//'):
                img_url = 'https:' + img_url
            # 去掉图片尺寸后缀
            img_url = re.sub(r'_\d+w_\d+h_\d+\.jpg$', '.jpg', img_url)
            product['image_url'] = img_url
        else:
            product['image_url'] = ''

        # 店铺名称
        shop_elem = item.select_one('.store')
        if shop_elem:
            product['shop'] = shop_elem.get_text(strip=True)
        else:
            product['shop'] = ''

        # 商品ID - 从URL中提取
        if product.get('detail_url'):
            match = re.search(r'/(\d+)\.html', product['detail_url'])
            product['goods_id'] = match.group(1) if match else ''
        else:
            product['goods_id'] = ''

        return product

    def get_product_detail(self, url):
        """
        获取商品详情

        返回: dict 包含 detail, weight, unit 等信息
        """
        try:
            response = self.session.get(url, timeout=self.timeout)
            if response.status_code == 200:
                response.encoding = response.apparent_encoding or 'utf-8'
                return self._parse_detail_page(response.text)
        except Exception as e:
            print(f"[Crawler] 获取详情异常: {e}")

        return {}

    def _parse_detail_page(self, html):
        """解析商品详情页面"""
        detail_info = {}

        try:
            soup = BeautifulSoup(html, 'html.parser')

            # 商品详情（纯文本）
            detail_elem = soup.select_one('#productDetail, .product-detail, #description')
            if detail_elem:
                for tag in detail_elem.find_all(['script', 'style']):
                    tag.decompose()
                detail_info['detail'] = detail_elem.get_text(strip=True)[:2000]
            else:
                detail_info['detail'] = ''

            # 价格（从span.price获取）
            price_elems = soup.find_all('span', class_='price')
            for pe in price_elems:
                text = pe.get_text(strip=True)
                if '¥' in text and re.search(r'\d', text):
                    price_match = re.search(r'[\d.]+', text)
                    if price_match:
                        try:
                            detail_info['price'] = float(price_match.group())
                            break
                        except:
                            pass

            # 规格重量 - 从参数区域获取
            param_elem = soup.select_one('[class*="param"]')
            if param_elem:
                param_text = param_elem.get_text(strip=True)
                # 提取净含量
                weight_match = re.search(r'净含量[：:]*(\d+[gGmlLmM克毫升级]+)', param_text)
                if weight_match:
                    detail_info['weight'] = weight_match.group(1)
                else:
                    detail_info['weight'] = '500g'

                # 提取包装类型作为单位
                if '箱装' in param_text:
                    detail_info['unit'] = '箱'
                elif '袋装' in param_text:
                    detail_info['unit'] = '袋'
                elif '盒装' in param_text:
                    detail_info['unit'] = '盒'
                else:
                    detail_info['unit'] = '袋'

                # 提取品牌作为介绍
                brand_match = re.search(r'品牌[：:]*([^\s]+)', param_text)
                if brand_match:
                    detail_info['brand'] = brand_match.group(1)
            else:
                detail_info['weight'] = '500g'
                detail_info['unit'] = '袋'

            # 商品介绍 - 从完整标题获取前100字
            title_elem = soup.select_one('h1.product-title, #productTitle, h1[class*="title"]')
            if title_elem:
                detail_info['intro'] = title_elem.get_text(strip=True)[:100]
            else:
                detail_info['intro'] = detail_info.get('detail', '')[:100] or '优质商品'

        except Exception as e:
            print(f"[Crawler] 解析详情异常: {e}")

        return detail_info

    def search_all_pages(self, keyword, max_pages=5):
        """
        搜索多页商品

        keyword: 搜索关键词
        max_pages: 最大页数
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


def test_crawler():
    """测试爬虫"""
    crawler = SuningCrawler()
    products = crawler.search_products('零食', page=1)
    print(f"\n获取到 {len(products)} 个商品")
    if products:
        print("\n第一个商品:")
        for k, v in products[0].items():
            print(f"  {k}: {str(v)[:60]}")


if __name__ == '__main__':
    test_crawler()
