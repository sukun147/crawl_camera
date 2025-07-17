import json
import time

from curl_cffi import requests
from fake_useragent import UserAgent
from lxml import etree

# 初始化UserAgent对象
ua = UserAgent()


def get_dynamic_headers():
    """动态生成headers"""
    return {
        'User-Agent': ua.random,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Referer': 'https://search.ccgp.gov.cn/bxsearch?searchtype=2&page_index=1&bidSort=&buyerName=&projectId=&pinMu=&bidType=7&dbselect=bidx&kw=%E6%91%84%E5%83%8F%E5%A4%B4&start_time=2025%3A01%3A01&end_time=2025%3A07%3A17&timeType=6&displayZone=&zoneId=&pppStatus=0&agentName='
    }


def get_html(params):
    response = requests.get('https://search.ccgp.gov.cn/bxsearch', params=params, headers=get_dynamic_headers(),
                            impersonate="chrome136", timeout=10)
    response.encoding = 'utf-8'
    return response.text


def parse(page,html):
    tree = etree.HTML(html)
    hrefs = tree.xpath('//ul[@class="vT-srch-result-list-bid"]/li/a/@href')
    all_data = {}  # 使用字典而不是列表来存储数据
    for index, href in enumerate(hrefs, start=1):
        print(href)
        item_data = {
            "url": href,
            "relevant_rows": {}  # 使用字典存储相关行
        }

        res = requests.get(href, impersonate="chrome136")
        res.encoding = 'utf-8'
        tree_info = etree.HTML(res.text)

        # 采购单位和时间
        table_ = tree_info.xpath('//div[@class="table"]/table')[0]
        item_data["unit"] = table_.xpath('.//tr[4]/td[2]/text()')[0]
        item_data["time"] = table_.xpath('.//tr[5]/td[4]/text()')[0]

        tables = tree_info.xpath('//div[@class="vF_detail_content"]//table')

        row_counter = 1  # 行计数器

        for table in tables:
            # 提取表头
            headers = []
            thead_th = table.xpath('.//thead//th[not(ancestor::script) and not(ancestor::style)]')
            if thead_th:
                headers = [
                    ''.join(th.xpath('.//text()[not(ancestor::script) and not(ancestor::style)]')).strip()
                    for th in thead_th
                    if ''.join(th.xpath('.//text()[not(ancestor::script) and not(ancestor::style)]')).strip()
                ]
            else:
                all_tr = table.xpath('.//tr[not(ancestor::script) and not(ancestor::style)]')
                for tr in all_tr:
                    tr_th = tr.xpath('./th[not(ancestor::script) and not(ancestor::style)]')
                    if tr_th:
                        headers = [
                            ''.join(th.xpath('.//text()[not(ancestor::script) and not(ancestor::style)]')).strip()
                            for th in tr_th
                            if ''.join(th.xpath('.//text()[not(ancestor::script) and not(ancestor::style)]')).strip()
                        ]
                        break
                    tr_td = tr.xpath('./td[not(ancestor::script) and not(ancestor::style)]')
                    if tr_td and any(
                            ''.join(td.xpath('.//text()[not(ancestor::script) and not(ancestor::style)]')).strip()
                            for td in tr_td):
                        headers = [
                            ''.join(td.xpath('.//text()[not(ancestor::script) and not(ancestor::style)]')).strip()
                            for td in tr_td
                            if ''.join(td.xpath('.//text()[not(ancestor::script) and not(ancestor::style)]')).strip()
                        ]
                        break

            # 提取数据行
            rows = []
            tbody_rows = table.xpath('.//tbody/tr[not(ancestor::script) and not(ancestor::style)]')
            if tbody_rows:
                if thead_th:
                    rows = tbody_rows
                else:
                    header_row_index = 0
                    for i, tr in enumerate(tbody_rows):
                        cells = [
                            ''.join(e.xpath('.//text()[not(ancestor::script) and not(ancestor::style)]')).strip()
                            for e in tr.xpath(
                                './th[not(ancestor::script) and not(ancestor::style)] | ./td[not(ancestor::script) and not(ancestor::style)]')
                            if ''.join(e.xpath('.//text()[not(ancestor::script) and not(ancestor::style)]')).strip()
                        ]
                        if cells == headers:
                            header_row_index = i
                            break
                    rows = tbody_rows[header_row_index + 1:]
            else:
                all_tr = table.xpath('.//tr[not(ancestor::script) and not(ancestor::style)]')
                header_row_index = 0
                for i, tr in enumerate(all_tr):
                    cells = [
                        ''.join(e.xpath('.//text()[not(ancestor::script) and not(ancestor::style)]')).strip()
                        for e in tr.xpath(
                            './th[not(ancestor::script) and not(ancestor::style)] | ./td[not(ancestor::script) and not(ancestor::style)]')
                        if ''.join(e.xpath('.//text()[not(ancestor::script) and not(ancestor::style)]')).strip()
                    ]
                    if cells == headers:
                        header_row_index = i
                        break
                rows = all_tr[header_row_index + 1:]

            # 处理数据行，只保留包含摄像头
            for row in rows:
                cells = [
                    ''.join(td.xpath('.//text()[not(ancestor::script) and not(ancestor::style)]')).strip()
                    for td in row.xpath('./td[not(ancestor::script) and not(ancestor::style)]')
                    if ''.join(td.xpath('.//text()[not(ancestor::script) and not(ancestor::style)]')).strip()
                ]

                # 检查是否包含关键词
                if any(('摄像头' in cell) for cell in cells):
                    if headers and len(headers) == len(cells):
                        row_data = {}
                        for i in range(len(headers)):
                            if (cells[i] and headers[i] and
                                    'script' not in headers[i].lower() and
                                    'style' not in headers[i].lower() and
                                    'script' not in cells[i].lower() and
                                    'style' not in cells[i].lower()):
                                row_data[headers[i]] = cells[i].replace('                                                ','')

                        if row_data:
                            item_data["relevant_rows"][f"row_{row_counter}"] = row_data
                            row_counter += 1

        if item_data["relevant_rows"]:  # 只有当有相关行时才添加
            all_data[f'page{page}_{index}'] = item_data

    return all_data


def main():
    filename = 'data/purchase_cn.json'
    all_data = {}  # 改了个更明确的变量名
    for page in range(1, 28):
        params = {
            'searchtype': '2',
            'page_index': page,
            'bidSort': '',
            'buyerName': '',
            'projectId': '',
            'pinMu': '',
            'bidType': '7',
            'dbselect': 'bidx',
            'kw': '摄像头',
            'start_time': '2025:01:01',
            'end_time': '2025:07:17',
            'timeType': '5',
            'displayZone': '',
            'zoneId': '',
            'pppStatus': '0',
            'agentName': '',
        }
        html = get_html(params)
        page_data = parse(page, html)
        all_data.update(page_data)
        print(f'第{page}页已采集完毕')
        time.sleep(2)
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=4)  # 添加了要保存的数据和格式化参数

    print(f"所有数据已保存到 {filename}")


if __name__ == '__main__':
    main()
