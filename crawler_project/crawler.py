"""
京东爬虫模块
"""
import re
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
from config import JD_SEARCH_URL, CRAWLER_CONFIG, CATEGORY_KEYWORDS, CATEGORY_MATCH_KEYWORDS


class JDCrawler:
    """京东商品爬虫"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(CRAWLER_CONFIG['headers'])
        self.delay = CRAWLER_CONFIG['delay']
        self.timeout = CRAWLER_CONFIG['timeout']

    def _get(self, url, retries=0):
        """带重试的GET请求"""
        try:
            response = self.session.get(url, timeout=self.timeout)
            if response.status_code == 200:
                # 尝试设置编码
                response.encoding = response.apparent_encoding or 'utf-8'
                return response.text
            else:
                print(f"[Crawler] HTTP {response.status_code}: {url}")
        except requests.RequestException as e:
            print(f"[Crawler] 请求异常: {e}")

        # 重试
        if retries < CRAWLER_CONFIG['max_retries']:
            time.sleep(self.delay * (retries + 1))
            return self._get(url, retries + 1)

        return None

    def search_products(self, keyword, page=1, per_page=30):
        """
        搜索京东商品

        keyword: 搜索关键词
        page: 页码
        per_page: 每页数量

        返回: 商品列表
        """
        params = {
            'keyword': keyword,
            'enc': 'utf-8',
            'wq': keyword,
            'pvid': '33_se_0_0_0',
        }

        # 京东搜索URL
        url = f"{JD_SEARCH_URL}?keyword={quote(keyword)}&enc=utf-8&wq={quote(keyword)}&page={page * 2 - 1}"

        print(f"[Crawler] 搜索: {keyword} 第{page}页")

        html = self._get(url)
        if not html:
            print(f"[Crawler] 获取页面失败: {keyword}")
            return []

        products = self._parse_search_page(html, keyword)
        return products

    def _parse_search_page(self, html, keyword):
        """解析搜索结果页面"""
        products = []

        try:
            soup = BeautifulSoup(html, 'html.parser')

            # 京东商品列表在 <ul class="gl-warp clearfix"> 中
            product_list = soup.select('ul.gl-warp > li')

            for item in product_list:
                try:
                    product = self._extract_product_info(item, keyword)
                    if product:
                        products.append(product)
                except Exception as e:
                    continue

        except Exception as e:
            print(f"[Crawler] 解析页面异常: {e}")

        return products

    def _extract_product_info(self, item, keyword):
        """从商品列表项提取商品信息"""
        product = {}

        # 商品名称 - 在 <div class="p-name"> 或 <em class="p-name-type"> 后的 <a> 标签
        name_elem = item.select_one('.p-name a, .p-name em a')
        if name_elem:
            product['pname'] = name_elem.get_text(strip=True)
        else:
            name_elem = item.select_one('.p-name')
            if name_elem:
                product['pname'] = name_elem.get_text(strip=True)
            else:
                return None

        # 商品价格
        price_elem = item.select_one('.p-price i, .p-price strong i')
        if price_elem:
            try:
                product['price'] = float(price_elem.get_text(strip=True))
            except:
                product['price'] = 0.0
        else:
            product['price'] = 0.0

        # 商品图片
        img_elem = item.select_one('.p-img img')
        if img_elem:
            # 优先获取 data-src，其次是 src
            product['image_url'] = img_elem.get('data-src') or img_elem.get('src') or ''
        else:
            product['image_url'] = ''

        # 店铺名称
        shop_elem = item.select_one('.p-shop a, .p-shop span')
        if shop_elem:
            product['shop'] = shop_elem.get_text(strip=True)
        else:
            product['shop'] = ''

        # 商品ID
        sku_match = re.search(r'data-sku="(\d+)"', str(item))
        if sku_match:
            product['sku'] = sku_match.group(1)
        else:
            product['sku'] = ''

        # 商品链接
        link_elem = item.select_one('.p-img a, .p-name a')
        if link_elem:
            product['detail_url'] = 'https:' + link_elem.get('href', '')
        else:
            product['detail_url'] = ''

        # 分类（使用搜索关键词对应的分类）
        product['tno'] = self._match_category(product['pname'])

        # 商品介绍（从标题提取前50字）
        product['intro'] = product['pname'][:50]

        return product

    def _match_category(self, pname):
        """根据商品名称匹配分类"""
        pname_lower = pname.lower()

        for tno, keywords in CATEGORY_MATCH_KEYWORDS.items():
            for kw in keywords:
                if kw.lower() in pname_lower:
                    return tno

        # 默认返回第一个分类（零食）
        return '2083190223734308864'

    def get_product_detail(self, url):
        """
        获取商品详情

        返回: dict 包含 detail, weight, unit 等信息
        """
        html = self._get(url)
        if not html:
            return {}

        detail_info = {}

        try:
            soup = BeautifulSoup(html, 'html.parser')

            # 商品详情（纯文本）
            detail_elem = soup.select_one('#detail .detail-content, #product-detail, .p-detail')
            if detail_elem:
                # 移除script和style标签
                for tag in detail_elem.find_all(['script', 'style']):
                    tag.decompose()
                detail_info['detail'] = detail_elem.get_text(strip=True)[:2000]
            else:
                detail_info['detail'] = ''

            # 规格重量
            weight_elem = soup.select_one('.summary-weight, .product-detail-summary li:contains("重量")')
            if weight_elem:
                weight_text = weight_elem.get_text(strip=True)
                weight_match = re.search(r'(\d+[gGmlLmM]+)', weight_text)
                if weight_match:
                    detail_info['weight'] = weight_match.group(1)
                else:
                    detail_info['weight'] = '500g'
            else:
                detail_info['weight'] = '500g'

            # 单位
            detail_info['unit'] = '袋'

        except Exception as e:
            print(f"[Crawler] 解析详情异常: {e}")

        return detail_info

    def search_all_pages(self, keyword, max_pages=5, per_page=30):
        """
        搜索多页商品

        keyword: 搜索关键词
        max_pages: 最大页数
        per_page: 每页数量
        """
        all_products = []

        for page in range(1, max_pages + 1):
            products = self.search_products(keyword, page, per_page)
            if not products:
                break

            all_products.extend(products)
            print(f"[Crawler] {keyword} 第{page}页: 获取 {len(products)} 个商品")

            # 翻页间隔
            if page < max_pages:
                time.sleep(self.delay)

        return all_products


def test_crawler():
    """测试爬虫"""
    crawler = JDCrawler()
    products = crawler.search_products('零食', page=1)
    print(f"获取到 {len(products)} 个商品")
    if products:
        print("第一个商品:", products[0])


if __name__ == '__main__':
    test_crawler()
