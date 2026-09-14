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

def crawl_by_keyword(keyword, tno, max_pages=2):
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
        for page_num in range(1, max_pages + 1):
            url = f'https://search.suning.com/{keyword}/0/{page_num-1}.html'
            print(f'[Crawler] {keyword} 第{page_num}页')

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

                        if '满100' in pname or '进店' in pname or '大促' in pname or '正版' in pname or '绘本' in pname or '出版社' in pname:
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

                        # 访问详情页
                        try:
                            page.goto(detail_url, timeout=60000)
                            page.wait_for_timeout(3000)
                        except:
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
                            'tno': int(tno),
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
    tno = 2088620594038833152
    keywords = ['T恤', '衬衫', '裤子', '外套', '裙子', '羽绒服']

    total = 0
    for kw in keywords:
        print(f'\n{"="*50}')
        print(f'搜索: {kw}')
        print(f'{"="*50}')
        count = crawl_by_keyword(kw, tno, max_pages=2)
        total += count
        print(f'{kw} 完成: {count} 条')

    print(f'\n本次新增: {total} 条')