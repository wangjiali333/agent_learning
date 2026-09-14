"""
数据库操作模块
"""
import pymysql
from config import MYSQL_CONFIG


class DatabaseHelper:
    """数据库操作辅助类"""

    def __init__(self):
        self.connection = None
        self.cursor = None

    def connect(self):
        """建立数据库连接"""
        try:
            self.connection = pymysql.connect(**MYSQL_CONFIG)
            self.cursor = self.connection.cursor()
            print("[DB] 数据库连接成功")
            return True
        except Exception as e:
            print(f"[DB] 数据库连接失败: {e}")
            return False

    def close(self):
        """关闭数据库连接"""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
            print("[DB] 数据库连接已关闭")

    def insert_product(self, product):
        """
        插入商品数据

        product: dict，包含所有字段
        pno, tno, pname, price, pics, intro, store, weight, unit, detail, pdate, status
        """
        sql = """
        INSERT INTO productioninfo
        (pno, tno, pname, price, pics, intro, store, weight, unit, detail, pdate, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        try:
            self.cursor.execute(sql, (
                product['pno'],
                product['tno'],
                product['pname'],
                product['price'],
                product['pics'],
                product['intro'],
                product['store'],
                product['weight'],
                product['unit'],
                product['detail'],
                product['pdate'],
                product['status']
            ))
            self.connection.commit()
            return True
        except Exception as e:
            print(f"[DB] 插入数据失败: {e}")
            self.connection.rollback()
            return False

    def get_all_categories(self):
        """获取所有分类"""
        sql = "SELECT tno, tname FROM typeinfo WHERE status = 1"
        try:
            self.cursor.execute(sql)
            results = self.cursor.fetchall()
            categories = [(str(row[0]), row[1]) for row in results]
            print(f"[DB] 获取到 {len(categories)} 个分类")
            return categories
        except Exception as e:
            print(f"[DB] 获取分类失败: {e}")
            return []

    def get_product_count(self):
        """获取当前商品数量"""
        sql = "SELECT COUNT(*) FROM productioninfo"
        try:
            self.cursor.execute(sql)
            count = self.cursor.fetchone()[0]
            return count
        except Exception as e:
            print(f"[DB] 获取商品数量失败: {e}")
            return 0


def test_connection():
    """测试数据库连接"""
    db = DatabaseHelper()
    if db.connect():
        db.close()
        return True
    return False


if __name__ == '__main__':
    test_connection()
