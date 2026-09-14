"""
处理Web Scraper采集的CSV数据
将图片上传到MinIO，数据写入MySQL
"""
import csv
import re
import time
from datetime import datetime
from urllib.parse import urlparse

from snowflake import generate_id
from db_helper import DatabaseHelper
from minio_uploader import MinIOUploader


class CSVProcessor:
    """处理Web Scraper导出的CSV文件"""

    def __init__(self):
        self.db = DatabaseHelper()
        self.minio = MinIOUploader()
        self.category_keywords = {
            '零食': '2083190223734308864',
            '饮料': '2083190855883030528',
            '水果': '2083190999957372928',
            '糖果巧克力': '2083810791223459840',
            '生活用品': '2087704651808899072',
            '服装': '2088620594038833152'
        }

    def start(self):
        """启动处理"""
        print("=" * 60)
        print("CSV数据处理器启动")
        print("=" * 60)

        # 连接数据库
        if not self.db.connect():
            print("[ERROR] 数据库连接失败")
            return

        # 连接MinIO
        if not self.minio.connect():
            print("[ERROR] MinIO连接失败")
            self.db.close()
            return

        print("[OK] 所有连接就绪")

    def process_csv(self, csv_file, category=None):
        """
        处理CSV文件

        csv_file: CSV文件路径
        category: 分类名称（如"零食"），用于自动匹配tno
        """
        tno = self.category_keywords.get(category, '2083190223734308864') if category else '2083190223734308864'
        print(f"\n[INFO] 处理文件: {csv_file}")
        print(f"[INFO] 分类: {category} -> tno: {tno}")

        count = 0
        success = 0

        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)

                for row in reader:
                    count += 1
                    try:
                        # 解析CSV行
                        product = self._parse_row(row, tno)
                        if not product:
                            continue

                        # 上传图片
                        image_path = self._upload_image(product['image_url'], product['pno'])
                        product['pics'] = image_path or ''

                        # 写入数据库
                        if self.db.insert_product(product):
                            success += 1
                            print(f"[OK] #{success:04d} {product['pname'][:30]}... - ¥{product['price']}")

                        time.sleep(0.3)  # 避免过快

                    except Exception as e:
                        print(f"[ERROR] 处理行出错: {e}")
                        continue

        except FileNotFoundError:
            print(f"[ERROR] 文件不存在: {csv_file}")
        except Exception as e:
            print(f"[ERROR] 处理CSV出错: {e}")

        print(f"\n[RESULT] 处理完成: 共{count}行，成功{success}条")
        return success

    def _parse_row(self, row, tno):
        """解析CSV行"""
        # 尝试获取各种可能的字段名
        pname = row.get('pname') or row.get('name') or row.get('title') or row.get('商品名称', '')
        price_str = row.get('price') or row.get('Price') or row.get('价格', '0')
        image_url = row.get('image') or row.get('img') or row.get('image_url') or row.get('图片', '')

        # 清理数据
        pname = pname.strip() if pname else ''
        if not pname:
            return None

        # 解析价格
        try:
            price = float(re.search(r'[\d.]+', price_str).group())
        except:
            price = 0.0

        # 清理图片URL
        image_url = image_url.strip()

        # 生成雪花ID
        pno = generate_id()

        product = {
            'pno': pno,
            'tno': int(tno),
            'pname': pname[:50],
            'price': price,
            'pics': '',
            'image_url': image_url,
            'intro': pname[:50],
            'store': 100,
            'weight': '500g',
            'unit': '袋',
            'detail': pname,
            'pdate': datetime.now(),
            'status': 1
        }

        return product

    def _upload_image(self, image_url, pno):
        """上传图片到MinIO"""
        if not image_url:
            return ''

        # 补全不完整的URL
        if image_url.startswith('//'):
            image_url = 'https:' + image_url
        elif image_url.startswith('/'):
            image_url = 'https://item.jd.com' + image_url

        # 获取扩展名
        ext = self._get_ext(image_url)
        object_name = f"goods_files/{pno}.{ext}"

        result = self.minio.upload_image(image_url, object_name)
        return result or ''

    def _get_ext(self, url):
        """从URL获取扩展名"""
        parsed = urlparse(url)
        path = parsed.path.lower()
        if '.jpg' in path:
            return 'jpg'
        elif '.png' in path:
            return 'png'
        elif '.gif' in path:
            return 'gif'
        elif '.webp' in path:
            return 'webp'
        else:
            return 'jpg'

    def close(self):
        """关闭连接"""
        self.db.close()


def main():
    """主函数"""
    processor = CSVProcessor()
    processor.start()

    print("\n请输入CSV文件路径和分类名称")
    print("格式: csv_file_path,category_name")
    print("示例: data/snacks.csv,零食")
    print("输入空行结束")

    while True:
        try:
            line = input("\n> ").strip()
            if not line:
                break

            parts = line.split(',')
            if len(parts) >= 2:
                csv_file = parts[0].strip()
                category = parts[1].strip()
                processor.process_csv(csv_file, category)
            else:
                print("格式错误")

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"错误: {e}")

    processor.close()
    print("\n处理完成")


if __name__ == '__main__':
    main()
