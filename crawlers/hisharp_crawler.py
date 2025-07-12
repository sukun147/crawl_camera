import time
from urllib.parse import urljoin

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import requests
from parsel import Selector

from .base_crawler import BaseCrawler


class HisharpCrawler(BaseCrawler):
    """
    Hisharp网站爬虫，继承自BaseCrawler
    """

    def __init__(self, data_dir="data"):
        """
        初始化Hisharp爬虫
        """
        # 调用父类初始化方法，使用Selenium
        super().__init__(brand_name="hisharp", data_dir=data_dir)

        # 设置Hisharp特定的属性
        self.base_url = "https://www.hisharp.com"

        # 设置起始URL列表
        self.start_urls = [
            "https://www.hisharp.com/zh-tw/product.php?act=list&cid=82",
            "https://www.hisharp.com/zh-tw/product.php?act=list&cid=88",
            "https://www.hisharp.com/zh-tw/product.php?act=list&cid=88&lang_id=1&page=2"
        ]

    def get_selector(self, url):
        """
        使用requests获取页面的Selector对象

        Args:
            url: 要获取的页面URL

        Returns:
            Selector对象，失败则返回None
        """
        try:
            response = requests.get(url, timeout=20)
            response.raise_for_status()
            self.logger.info(f"成功获取页面: {url}")
            return Selector(text=response.text)
        except Exception as e:
            self.logger.error(f"获取页面内容时出错 {url}: {str(e)}")
            return None

    def get_links_from_page(self, url, selector=None):
        """
        从页面获取所有.pic-box的href属性

        Args:
            url: 要获取链接的页面URL
            selector: CSS选择器（可选）

        Returns:
            产品链接列表
        """
        links = []
        selector = self.get_selector(url)
        if not selector:
            self.logger.warning(f"无法获取页面选择器: {url}")
            return links

        # 获取所有.pic-box的href属性
        pic_boxes = selector.css('.pic-box')
        for box in pic_boxes:
            href = box.attrib.get('href', '')
            if href:
                # 拼接完整URL
                full_url = urljoin(self.base_url, href)
                links.append(full_url)

        self.logger.info(f"从页面 {url} 获取到 {len(links)} 个产品链接")
        return links

    def extract_product_details(self, url):
        """
        使用Selenium从产品页面提取产品详情

        Args:
            url: 产品页面URL

        Returns:
            产品数据字典或None（如果提取失败）
        """
        try:
            self.logger.info(f"开始提取产品详情: {url}")
            self.driver.get(url)
            time.sleep(2)  # 等待页面加载

            # 获取产品ID (h1 > span.en的text)
            try:
                product_id_elem = self.wait.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, 'h1 > span.en')
                ))
                product_id = product_id_elem.text.strip()
                if not product_id:
                    self.logger.warning(f"无法获取产品ID {url}")
                    return None
            except (TimeoutException, NoSuchElementException) as e:
                self.logger.error(f"无法获取产品ID {url}: {str(e)}")
                return None

            # 获取产品名称 (h1 > span.ch的text)
            try:
                product_name_elem = self.driver.find_element(By.CSS_SELECTOR, 'h1 > span.ch')
                product_name = product_name_elem.text.strip()
                if not product_name:
                    product_name = "未知名称"
            except NoSuchElementException as e:
                self.logger.error(f"无法获取产品名称 {url}: {str(e)}")
                product_name = "未知名称"

            # 点击"產品規格"按钮
            try:
                spec_button = self.wait.until(EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, 'a[title="產品規格"]')
                ))
                spec_button.click()
                time.sleep(1.5)  # 等待规格内容加载
            except (TimeoutException, NoSuchElementException) as e:
                self.logger.warning(f"无法点击产品规格按钮 {url}: {str(e)}")
                try:
                    spec_button = self.driver.find_element(By.CSS_SELECTOR, 'a[title="產品規格"]')
                    self.driver.execute_script("arguments[0].click();", spec_button)
                    time.sleep(1.5)
                except Exception as js_e:
                    print(f"JavaScript点击產品規格按钮失败 {url}: {str(js_e)}")

            # 获取参数表格
            params = []
            try:
                table_rows = self.driver.find_elements(By.CSS_SELECTOR, 'tbody > tr')
                for row in table_rows:
                    cells = row.find_elements(By.TAG_NAME, 'td')
                    if len(cells) >= 2:
                        param_name = cells[0].text.strip()
                        param_value = cells[1].text.strip()

                        if param_name:
                            params.append({
                                "paramName": param_name,
                                "param": param_value
                            })
            except Exception as e:
                self.logger.warning(f"获取参数表格时出错 {url}: {str(e)}")

            # 构建产品数据
            product_data = {
                'product_id': product_id,
                'product_name': product_name,
                'params': params
            }

            self.logger.info(f"成功提取产品详情: {product_id}")
            return product_data

        except Exception as e:
            self.logger.error(f"提取产品详情时出错 {url}: {str(e)}")
            return None

    def process_category_page(self, url):
        """
        处理分类页面，获取所有产品链接

        Args:
            url: 分类页面URL

        Returns:
            产品链接列表
        """
        return self.get_links_from_page(url)
