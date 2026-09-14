"""
MinIO图片上传模块
"""
import os
import requests
from io import BytesIO
from minio import Minio
from minio.error import S3Error
from config import MINIO_CONFIG, MINIO_IMAGE_PATH


class MinIOUploader:
    """MinIO图片上传器"""

    def __init__(self):
        self.client = None
        self.bucket = MINIO_CONFIG['bucket']
        self.image_path = MINIO_IMAGE_PATH

    def connect(self):
        """连接MinIO"""
        try:
            self.client = Minio(
                endpoint=MINIO_CONFIG['endpoint'],
                access_key=MINIO_CONFIG['access_key'],
                secret_key=MINIO_CONFIG['secret_key'],
                secure=MINIO_CONFIG['secure']
            )

            # 检查bucket是否存在，不存在则创建
            found = self.client.bucket_exists(self.bucket)
            if not found:
                self.client.make_bucket(self.bucket)
                print(f"[MinIO] 创建Bucket: {self.bucket}")
            else:
                print(f"[MinIO] 连接成功，Bucket: {self.bucket} 已存在")

            return True
        except S3Error as e:
            print(f"[MinIO] 连接失败: {e}")
            return False
        except Exception as e:
            print(f"[MinIO] 连接异常: {e}")
            return False

    def upload_image(self, image_url, object_name):
        """
        从URL下载图片并上传到MinIO

        image_url: 图片URL
        object_name: 对象名称（如 'goods_files/123456789.jpg'）

        返回: 上传后的路径，失败返回None
        """
        try:
            # 下载图片
            response = requests.get(image_url, timeout=30)
            if response.status_code != 200:
                print(f"[MinIO] 图片下载失败: {image_url}")
                return None

            image_data = BytesIO(response.content)

            # 上传到MinIO
            self.client.put_object(
                bucket_name=self.bucket,
                object_name=object_name,
                data=image_data,
                length=len(response.content),
                content_type=response.headers.get('Content-Type', 'image/jpeg')
            )

            # 返回相对路径
            return object_name

        except S3Error as e:
            print(f"[MinIO] 上传失败: {e}")
            return None
        except Exception as e:
            print(f"[MinIO] 上传异常: {e}")
            return None

    def upload_local_image(self, local_path, object_name):
        """
        上传本地图片到MinIO

        local_path: 本地文件路径
        object_name: 对象名称

        返回: 上传后的路径，失败返回None
        """
        try:
            with open(local_path, 'rb') as f:
                file_data = f.read()

            self.client.put_object(
                bucket_name=self.bucket,
                object_name=object_name,
                data=BytesIO(file_data),
                length=len(file_data),
                content_type='image/jpeg'
            )

            return object_name

        except Exception as e:
            print(f"[MinIO] 上传本地图片失败: {e}")
            return None

    def get_image_url(self, object_name):
        """获取图片URL"""
        return f"http://{MINIO_CONFIG['endpoint']}/{self.bucket}/{object_name}"


def test_minio():
    """测试MinIO连接"""
    uploader = MinIOUploader()
    return uploader.connect()


if __name__ == '__main__':
    test_minio()
