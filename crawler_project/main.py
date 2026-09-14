"""
爬虫主入口 - 苏宁易购版本
"""
import time
from datetime import datetime

from config import CATEGORY_KEYWORDS
from snowflake import generate_id
from db_helper import DatabaseHelper
from minio_uploader import MinIOUploader
from suning_crawler import SuningCrawler


class ProductCrawler:
    """商品爬虫主类"""

    def __init__(self, target_count=500):
        self.target_count = target_count
        self.crawler = SuningCrawler()
        self.db = DatabaseHelper()
        self.minio = MinIOUploader()
        self.collected_count = 0

    def start(self):
        """启动爬虫"""
        print("=" * 60)
        print("苏宁易购商品爬虫启动")
        print(f"目标: {self.target_count} 条商品")
        print("=" * 60)

        # 1. 连接数据库
        if not self.db.connect():
            print("[ERROR] 数据库连接失败，程序退出")
            return

        # 2. 连接MinIO
        if not self.minio.connect():
            print("[ERROR] MinIO连接失败，程序退出")
            self.db.close()
            return

        # 3. 按分类爬取
        try:
            self._crawl_by_categories()
        except KeyboardInterrupt:
            print("\n[INFO] 用户中断爬虫")
        except Exception as e:
            print(f"[ERROR] 爬虫异常: {e}")
        finally:
            self.db.close()

        print("=" * 60)
        print(f"爬虫结束，共采集 {self.collected_count} 条商品")
        print("=" * 60)

    def _crawl_by_categories(self):
        """按分类爬取商品"""
        # 计算每个分类需要爬取的数量
        category_count = len(CATEGORY_KEYWORDS)
        per_category = max(10, self.target_count // category_count)

        print(f"\n共有 {category_count} 个分类，每个分类计划爬取约 {per_category} 个商品\n")

        for tno, keyword in CATEGORY_KEYWORDS.items():
            if self.collected_count >= self.target_count:
                print("[INFO] 已达到目标数量，停止爬取")
                break

            print(f"\n{'='*50}")
            print(f"开始爬取分类: {keyword} (tno: {tno})")
            print(f"{'='*50}")

            # 搜索该分类的商品（多页）
            products = self.crawler.search_all_pages(keyword, max_pages=5)

            print(f"[INFO] {keyword} 共获取 {len(products)} 个商品列表")

            # 处理每个商品
            for product in products:
                if self.collected_count >= self.target_count:
                    break

                # 获取商品详情（包含价格）
                if product.get('detail_url'):
                    time.sleep(0.5)
                    detail_info = self.crawler.get_product_detail(product['detail_url'])
                    product.update(detail_info)
                else:
                    product['detail'] = product.get('pname', '')
                    product['weight'] = '500g'
                    product['unit'] = '袋'

                # 下载并上传图片
                if product.get('image_url'):
                    time.sleep(0.3)
                    image_path = self._upload_product_image(product)
                    product['pics'] = image_path or ''
                else:
                    product['pics'] = ''

                # 生成雪花ID
                pno = generate_id()

                # 构建商品数据
                product_data = {
                    'pno': pno,
                    'tno': int(tno),
                    'pname': product.get('pname', '')[:50],
                    'price': product.get('price', 0.0),
                    'pics': product.get('pics', ''),
                    'intro': product.get('pname', '')[:200],
                    'store': 100,
                    'weight': product.get('weight', '500g'),
                    'unit': product.get('unit', '袋'),
                    'detail': product.get('detail', '')[:2000],
                    'pdate': datetime.now(),
                    'status': 1
                }

                # 写入数据库
                if self.db.insert_product(product_data):
                    self.collected_count += 1
                    print(f"[OK] #{self.collected_count:04d} {product_data['pname'][:30]}... - ¥{product_data['price']}")

                # 避免请求过快
                time.sleep(0.5)

            print(f"[INFO] {keyword} 分类爬取完成")

        # 打印最终统计
        final_count = self.db.get_product_count()
        print(f"\n[FINAL] 数据库中商品总数: {final_count}")

    def _upload_product_image(self, product):
        """
        下载并上传商品图片到MinIO

        返回: MinIO中的图片路径
        """
        image_url = product.get('image_url', '')
        if not image_url:
            return ''

        # 生成文件名
        pno = generate_id()
        ext = self._get_image_ext(image_url)
        object_name = f"goods_files/{pno}.{ext}"

        # 上传到MinIO
        result = self.minio.upload_image(image_url, object_name)

        if result:
            return result
        else:
            return ''

    def _get_image_ext(self, url):
        """从URL获取图片扩展名"""
        if '.jpg' in url.lower():
            return 'jpg'
        elif '.png' in url.lower():
            return 'png'
        elif '.gif' in url.lower():
            return 'gif'
        elif '.webp' in url.lower():
            return 'webp'
        else:
            return 'jpg'


def main():
    """主函数"""
    print("请选择运行模式：")
    print("1. 测试模式 (爬取少量数据)")
    print("2. 完整模式 (爬取500条商品)")
    print("3. 自定义数量")

    choice = input("请输入选项 (1/2/3): ").strip()

    if choice == '1':
        crawler = ProductCrawler(target_count=10)
        crawler.start()
    elif choice == '2':
        crawler = ProductCrawler(target_count=500)
        crawler.start()
    elif choice == '3':
        try:
            count = int(input("请输入目标数量: ").strip())
            crawler = ProductCrawler(target_count=count)
            crawler.start()
        except ValueError:
            print("无效的数量，退出")
    else:
        print("无效选项，退出")


if __name__ == '__main__':
    main()
