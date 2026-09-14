# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')
import time
import json
from datetime import datetime
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import re

from snowflake import generate_id
from db_helper import DatabaseHelper
from minio_uploader import MinIOUploader

# 非服装商品关键词
EXCLUDE_KEYWORDS = [
    '洗衣', '衣架', '衣撑', '衣帽架', '鞋柜', '鞋盒', '除毛', '修剪器',
    '吸色片', '去黄', '去渍', '长条凳', '工具挂钩', '花边', '布花边',
    '衣护', '晾衣', '挂衣', '收纳箱', '收纳盒', '整理箱', '压缩袋',
    '洗衣机', '清洁', '消毒液', '柔顺剂', '护理剂', '洗护'
]

def is_clothing(pname):
    """判断是否是服装类商品"""
    pname_lower = pname.lower()
    for kw in EXCLUDE_KEYWORDS:
        if kw in pname_lower:
            return False

    # 服装关键词
    clothing_keywords = ['T恤', '衬衫', '裤子', '裙子', '外套', '大衣', '羽绒服',
                         '棉服', '毛衣', '针织', '卫衣', '运动服', '睡衣', '内衣',
                         '袜子', '围巾', '帽子', '手套', '皮带', '领带', '西装',
                         '牛仔', '牛仔裤', '短裙', '连衣裙', '礼服', '旗袍',
                         ' Polo ', 'polo', 'T恤', 't恤', '体恤', '衫', '褂',
                         '男装', '女装', '童装', '男童', '女童', '男士', '女士',
                         '冬装', '夏装', '春装', '秋装', '外套', '上装', '下装',
                         '丝袜', '连裤袜', '打底裤', '保暖衣', '内衣', '文胸',
                         '背心', '吊带', '泳装', '沙滩裤', '运动裤', '休闲裤',
                         '阔腿裤', '短裤', '七分裤', '九分裤', '长裤']

    for kw in clothing_keywords:
        if kw in pname:
            return True

    return False

def crawl_clothing():
    """爬取服装类别"""
    cookies_file = 'suning_cookies.json'

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='zh-CN',
        )

        with open(cookies_file, 'r', encoding='utf-8') as f:
            cookies = json.load(f)
        context.add_cookies(cookies)

        page = context.new_page()

        db = DatabaseHelper()
        minio = MinIOUploader()
        db.connect()
        minio.connect()

        count = 0
        for page_num in range(1, 5):
            url = f'https://search.suning.com/服装/0/{page_num-1}.html'
            print(f'[Crawler] 服装 第{page_num}页')

            try:
                page.goto(url, timeout=60000)
                page.wait_for_timeout(2000)

                html = page.content()
                soup = BeautifulSoup(html, 'html.parser')
                product_boxes = soup.select('div.product-box')

                print(f'  获取 {len(product_boxes)} 个商品')

                for box in product_boxes:
                    try:
                        img_elem = box.select_one('img')
                        if not img_elem:
                            continue

                        pname = img_elem.get('alt', '').strip()
                        if not pname:
                            continue

                        # 跳过广告
                        if '满100' in pname or '进店' in pname or '大促' in pname:
                            continue

                        # 过滤非服装
                        if not is_clothing(pname):
                            print(f'  [SKIP] 非服装: {pname[:30]}')
                            continue

                        # 检查是否已存在
                        cursor = db.connection.cursor()
                        cursor.execute('SELECT pno FROM productioninfo WHERE pname = %s', (pname,))
                        if cursor.fetchone():
                            cursor.close()
                            continue
                        cursor.close()

                        # 商品链接
                        links = box.select('a[href*="product.suning.com"]')
                        if not links:
                            continue
                        detail_url = 'https:' + links[0].get('href', '').split('#')[0]

                        # 图片
                        img_url = img_elem.get('src') or img_elem.get('data-src') or ''
                        if img_url.startswith('//'):
                            img_url = 'https:' + img_url
                        img_url = re.sub(r'_\d+w_\d+h_\d+\.jpg$', '.jpg', img_url)

                        # 访问详情页获取价格
                        try:
                            page.goto(detail_url, timeout=60000)
                            page.wait_for_timeout(3000)
                        except:
                            print(f'  [SKIP] 访问详情页失败')
                            continue
                        content = page.content()
                        detail_soup = BeautifulSoup(content, 'html.parser')

                        # 价格
                        price_spans = detail_soup.find_all('span', class_='price')
                        price = 0.0
                        for ps in price_spans:
                            text = ps.get_text(strip=True)
                            if '¥' in text and re.search(r'\d', text):
                                m = re.search(r'[\d.]+', text)
                                if m:
                                    try:
                                        p_val = float(m.group())
                                        if p_val > 0 and p_val < 1000:
                                            price = p_val
                                            break
                                    except:
                                        pass

                        # 参数
                        param_elem = detail_soup.select_one('[class*="param"]')
                        if param_elem:
                            param_text = param_elem.get_text(strip=True)
                            wm = re.search(r'净含量[：:]*(\d+[gGmlLmM克毫升级]+)', param_text)
                            weight = wm.group(1) if wm else '500g'
                            if '箱装' in param_text:
                                unit = '箱'
                            elif '袋装' in param_text:
                                unit = '袋'
                            elif '盒装' in param_text:
                                unit = '盒'
                            elif '瓶装' in param_text:
                                unit = '瓶'
                            else:
                                unit = '件'

                            intro_parts = []
                            if '品牌：' in param_text:
                                bm = re.search(r'品牌[：:]*(.*?)[国产进口产地]', param_text)
                                if bm and bm.group(1).strip():
                                    intro_parts.append(bm.group(1).strip())
                            if '类别：' in param_text:
                                cm = re.search(r'类别[：:]*(.*?)[国产进口]', param_text)
                                if cm and cm.group(1).strip():
                                    intro_parts.append(cm.group(1).strip())
                            if '适用人群' in param_text:
                                gm = re.search(r'适用人群[：:]*(.*?)[适用季节]', param_text)
                                if gm and gm.group(1).strip():
                                    intro_parts.append(gm.group(1).strip())
                            intro = '-'.join(intro_parts) if intro_parts else '优质商品'
                        else:
                            weight = '500g'
                            unit = '件'
                            intro = '优质商品'

                        # 下载图片
                        pno = generate_id()
                        image_path = ''
                        if img_url:
                            try:
                                object_name = f'goods_files/{pno}.jpg'
                                image_path = minio.upload_image(img_url, object_name)
                            except:
                                pass

                        product_data = {
                            'pno': pno,
                            'tno': 2088620594038833152,
                            'pname': pname[:50],
                            'price': price,
                            'pics': image_path,
                            'intro': intro[:200],
                            'store': 100,
                            'weight': weight,
                            'unit': unit,
                            'detail': intro[:2000],
                            'pdate': datetime.now(),
                            'status': 1
                        }

                        if db.insert_product(product_data):
                            print(f'  [OK] {pname[:25]}... | ¥{price}')
                            count += 1

                        time.sleep(0.5)

                    except Exception as e:
                        continue

            except Exception as e:
                print(f'  错误: {e}')
                continue

        browser.close()
        db.close()

    return count

if __name__ == '__main__':
    print('=' * 50)
    print('开始爬取: 服装')
    print('=' * 50)
    count = crawl_clothing()
    print(f'服装 完成: {count} 条')