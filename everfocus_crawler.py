import time
import random
from urllib.parse import urljoin
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from base_crawler import BaseCrawler


class EverFocusCrawler(BaseCrawler):
    def __init__(self, data_dir="data"):
        # 调用父类初始化方法，启用Selenium
        super().__init__(brand_name="everfocus", data_dir=data_dir, use_selenium=True)

        # 设置基础URL
        self.base_url = "https://www.everfocus.com"

        # 设置起始URL（网络摄像机分类页面）
        self.start_urls = [
            "https://www.everfocus.com/tw/product/catalog.php?index_m1_id=3&index_m2_id=25&index_m3_id=76"]

    def get_links_from_page(self, url, selector=None):
        """使用Selenium获取页面中的产品链接"""
        links = []
        try:
            # 使用Selenium打开页面
            self.driver.get(url)
            time.sleep(2)  # 等待页面加载

            # 查找所有div.Img > a元素
            product_elements = self.driver.find_elements(By.CSS_SELECTOR, 'div.Img > a')

            for element in product_elements:
                href = element.get_attribute('href')
                if href:
                    # 处理相对URL
                    full_url = urljoin(self.base_url, href)
                    links.append(full_url)

            return links
        except Exception as e:
            print(f"获取产品链接时出错 {url}: {str(e)}")
            return []

    def extract_product_details(self, url):
        """使用Selenium从产品页面提取产品详情"""
        try:
            # 添加随机延迟，避免请求过于频繁
            time.sleep(random.uniform(1, 3))

            # 使用Selenium打开页面
            self.driver.get(url)
            time.sleep(2)  # 等待页面加载

            # 获取产品ID（div.introBox > div > h1的text）
            try:
                product_id_elem = self.wait.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, 'div.introBox > div > h1')
                ))
                product_id = product_id_elem.text.strip()
                if not product_id:
                    product_id = "未知ID"
            except (TimeoutException, NoSuchElementException) as e:
                print(f"无法获取产品ID {url}: {str(e)}")
                product_id = "未知ID"

            # 获取产品名称（div.introBox > div > b的text）
            try:
                name_elem = self.driver.find_element(By.CSS_SELECTOR, 'div.introBox > div > b')
                name = name_elem.text.strip()
                if not name:
                    name = "未知名称"
            except (TimeoutException, NoSuchElementException) as e:
                print(f"无法获取产品名称 {url}: {str(e)}")
                name = "未知名称"

            # 获取规格参数（div > table > tbody > tr）
            params = []
            try:
                spec_rows = self.driver.find_elements(By.CSS_SELECTOR, 'div > table > tbody > tr')

                for row in spec_rows:
                    # 提取每个单元格的文本
                    cells = row.find_elements(By.TAG_NAME, 'td')
                    if len(cells) >= 2:
                        # 获取第一个单元格的文本内容
                        param_name = cells[0].text.strip()
                        # 获取第二个单元格的文本内容
                        param_value = cells[1].text.strip()

                        # 只保存非空参数
                        if param_name and param_value:
                            params.append({
                                "paramName": param_name,
                                "param": param_value
                            })
            except Exception as e:
                print(f"提取规格参数时出错 {url}: {str(e)}")

            # 检查是否获取到规格参数
            if not params:
                print(f"未提取到任何规格参数 {url}")

            # 准备产品数据（按照新的格式）
            product_data = {
                'product_id': product_id,
                'product_name': name,
                'params': params
            }

            print(f"✓ 成功提取产品信息: {name} ({product_id})")
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
