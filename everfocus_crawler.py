import requests
import time
import random
from urllib.parse import urljoin
from parsel import Selector
from base_crawler import BaseCrawler


class EverFocusCrawler(BaseCrawler):
    def __init__(self, data_dir="data"):
        # 调用父类初始化方法，指定不使用Selenium
        super().__init__(brand_name="everfocus", data_dir=data_dir, use_selenium=False)

        # 设置基础URL
        self.base_url = "https://www.everfocus.com"

        # 设置起始URL（网络摄像机分类页面）
        self.start_urls = [
            "https://www.everfocus.com/tw/product/catalog.php?index_m1_id=3&index_m2_id=25&index_m3_id=76"]

        # 设置请求头
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }

    def get_links_from_page(self, url, selector=None):
        """获取页面中的产品链接"""
        links = []
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()  # 检查请求是否成功

            # 使用Parsel解析HTML
            sel = Selector(text=response.text)

            # 查找所有div.Img > a元素
            product_elements = sel.css('div.Img > a')

            for element in product_elements:
                href = element.attrib.get('href')
                if href:
                    # 处理相对URL
                    full_url = urljoin(self.base_url, href)
                    links.append(full_url)

            return links
        except Exception as e:
            print(f"获取产品链接时出错 {url}: {str(e)}")
            return []

    def extract_product_details(self, url):
        """从产品页面提取产品详情"""
        try:
            # 添加随机延迟，避免请求过于频繁
            time.sleep(random.uniform(1, 3))

            response = requests.get(url, headers=self.headers)
            response.raise_for_status()

            # 使用Parsel解析HTML
            sel = Selector(text=response.text)

            # 获取产品ID（div.introBox > div > h1的text）
            product_id = sel.css('div.introBox > div > h1::text').get('').strip()
            if not product_id:
                product_id = "未知ID"

            # 获取产品名称（div.introBox > div > b的text）
            name = sel.css('div.introBox > div > b::text').get('').strip()
            if not name:
                name = "未知名称"

            # 获取规格参数（div > table > tbody > tr）
            specs = {}
            spec_rows = sel.css('div > table > tbody > tr')

            for row in spec_rows:
                # 提取每个单元格的文本
                cells = row.css('td')
                if len(cells) >= 2:
                    # 获取第一个单元格的所有文本内容并连接
                    param_name = ''.join(cells[0].css('*::text').getall()).strip()
                    # 获取第二个单元格的所有文本内容并连接
                    param_value = ''.join(cells[1].css('*::text').getall()).strip()

                    # 只保存非空参数
                    if param_name and param_value:
                        specs[param_name] = param_value

            # 准备产品数据
            product_data = {
                'id': product_id,
                'name': name,
                'url': url,
                'specifications': specs
            }

            return product_data
        except Exception as e:
            print(f"提取产品详情时出错 {url}: {str(e)}")
            return None

    def process_category_page(self, url):
        """处理类别页面"""
        product_links = self.get_links_from_page(url)
        print(f"在类别页面 {url} 上找到 {len(product_links)} 个产品链接")
        return product_links


if __name__ == '__main__':
    data_dir = "data"  # 默认数据目录
    crawler = EverFocusCrawler(data_dir=data_dir)
    crawler.run()
