# MySQL配置
MYSQL_CONFIG = {
    'host': '127.0.0.1',
    'port': 3306,
    'user': 'root',
    'password': 'yy123456',
    'database': 'snacknet',
    'charset': 'utf8mb4'
}

# MinIO配置
MINIO_CONFIG = {
    'endpoint': '127.0.0.1:9000',
    'access_key': 'minioadmin',
    'secret_key': 'minioadmin',
    'bucket': 'snacknet',
    'secure': False  # 是否使用HTTPS
}

# 京东搜索基础URL
JD_SEARCH_URL = 'https://search.jd.com/Search'

# 分类与关键词映射
CATEGORY_KEYWORDS = {
    '2083190223734308864': '零食',
    '2083190855883030528': '饮料',
    '2083190999957372928': '水果',
    '2083810791223459840': '糖果巧克力',
    '2087704651808899072': '生活用品',
    '2088620594038833152': '服装'
}

# 分类关键词匹配（用于从商品标题判断分类）
CATEGORY_MATCH_KEYWORDS = {
    '2083190223734308864': ['零食', '薯片', '饼干', '糕点', '肉干', '卤味', '坚果', '海苔', '膨化', '辣条', '糖果', '巧克力', '果冻', '布丁'],
    '2083190855883030528': ['饮料', '汽水', '果汁', '奶茶', '咖啡', '茶', '水', '牛奶', '酸奶', '啤酒', '白酒', '红酒'],
    '2083190999957372928': ['水果', '苹果', '香蕉', '橙子', '葡萄', '草莓', '芒果', '猕猴桃', '蓝莓', '柚子', '菠萝', '椰子', '榴莲'],
    '2083810791223459840': ['糖果', '巧克力', '软糖', '硬糖', '牛轧糖', '口香糖', '薄荷糖', '果冻', '布丁', '雪糕', '冰淇淋'],
    '2087704651808899072': ['纸巾', '洗衣液', '洗发水', '沐浴露', '牙膏', '牙刷', '毛巾', '杯子', '收纳', '清洁', '卫生', '厨房', '日用品'],
    '2088620594038833152': ['衣服', 'T恤', '衬衫', '裤子', '裙子', '外套', '羽绒服', '卫衣', '运动服', '内衣', '袜子', '女装', '男装']
}

# 爬虫配置
CRAWLER_CONFIG = {
    'delay': 2,  # 请求间隔（秒）
    'timeout': 30,  # 请求超时（秒）
    'max_retries': 3,  # 最大重试次数
    'headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Connection': 'keep-alive',
    }
}

# MinIO图片存储路径前缀
MINIO_IMAGE_PATH = 'goods_files/'
