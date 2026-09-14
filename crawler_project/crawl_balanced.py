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

# 分类关键词配置
CATEGORY_KEYWORDS = {
    '2083190223734308864': ['零食', '薯片', '饼干', '坚果', '卤味', '辣条', '海苔', '糕点', '肉干'],
    '2083190855883030528': ['饮料', '汽水', '果汁', '奶茶', '咖啡', '茶', '牛奶', '酸奶', '啤酒'],
    '2083190999957372928': ['水果', '苹果', '香蕉', '橙子', '葡萄', '草莓', '芒果', '榴莲', '猕猴桃'],
    '2083810791223459840': ['糖果', '巧克力', '软糖', '奶糖', '口香糖', '薄荷糖', '果冻'],
    '2087704651808899072': ['纸巾', '洗衣液', '洗发水', '沐浴露', '牙膏', '牙刷', '毛巾', '收纳', '清洁'],
    '2088620594038833152': ['T恤', '衬衫', '裤子', '外套', '裙子', '卫衣', '牛仔裤', '运动服', '袜子']
}

def get_db_count(db, tno):
    cursor = db.connection.cursor()
    cursor.execute('SELECT COUNT(*) FROM productioninfo WHERE tno = %s', (tno,))
    count = cursor.fetchone()[0]
    cursor.close()
    return count

def is_duplicate(db, pname):
    cursor = db.connection.cursor()
    cursor.execute('SELECT pno FROM productioninfo WHERE pname = %s', (pname,))
    exists = cursor.fetchone()
    cursor.close()
    return exists is not None

def crawl_by_keyword(keyword, tno, max_pages=3):
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

            try:
                page.goto(url, timeout=60000)
                page.wait_for_timeout(2000)

                html = page.content()
                soup = BeautifulSoup(html, 'html.parser')
                product_boxes = soup.select('div.product-box')

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

                        # 去重检查
                        if is_duplicate(db, pname):
                            continue

                        links = box.select('a[href*="product.suning.com"]')
                        if not links:
                            continue
                        detail_url = 'https:' + links[0].get('href', '').split('#')[0]

                        img_url = img_elem.get('src') or img_elem.get('data-src') or ''
                        if img_url.startswith('//'):
                            img_url = 'https:' + img_url
                        img_url = re.sub(r'_\d+w_\d+h_\d+\.jpg$', '.jpg', img_url)

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
                                unit = '袋'

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
                            unit = '袋'
                            intro = '优质商品'

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
                            print(f'  [OK] {pname[:20]}... ¥{price}')
                            count += 1

                        time.sleep(0.5)

                    except Exception as e:
                        continue

            except Exception as e:
                continue

        browser.close()
        db.close()

    return count

if __name__ == '__main__':
    db = DatabaseHelper()
    db.connect()

    print('当前各分类数据量:')
    for tno, keywords in CATEGORY_KEYWORDS.items():
        count = get_db_count(db, tno)
        cat_name = keywords[0]
        print(f'  {cat_name}: {count} 条')

    print('\n开始均衡爬取...')

    total = 0
    for tno, keywords in CATEGORY_KEYWORDS.items():
        current = get_db_count(db, tno)
        target = 80
        need = max(0, target - current)

        if need == 0:
            print(f'\n{keywords[0]}: 已达目标({current}条)，跳过')
            continue

        print(f'\n{"="*50}')
        print(f'{keywords[0]}: 当前{current}条，需要{need}条')
        print(f'{"="*50}')

        cat_total = 0
        for kw in keywords:
            pages = 3 if need > 30 else 2
            print(f'\n  搜索: {kw}')
            count = crawl_by_keyword(kw, tno, max_pages=pages)
            cat_total += count
            if cat_total >= need:
                break
            time.sleep(1)

        print(f'\n{keywords[0]} 完成: {cat_total} 条')

        # 爬取完去重
        cursor = db.connection.cursor()
        cursor.execute('SELECT pname, COUNT(*) as cnt FROM productioninfo WHERE tno = %s GROUP BY pname HAVING COUNT(*) > 1', (tno,))
        dups = cursor.fetchall()
        for (pname, cnt) in dups:
            cursor.execute('SELECT pno FROM productioninfo WHERE pname = %s ORDER BY pno DESC LIMIT 1', (pname,))
            keep = cursor.fetchone()
            if keep:
                cursor.execute('DELETE FROM productioninfo WHERE pname = %s AND pno != %s', (pname, keep[0]))
        db.connection.commit()
        cursor.close()

        final = get_db_count(db, tno)
        print(f'{keywords[0]} 最终: {final} 条')

    db.close()

    print('\n' + '='*50)
    print('爬取完成!')