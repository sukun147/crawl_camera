import time
from urllib.parse import urljoin

import requests
from parsel import Selector
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from .base_crawler import BaseCrawler


class ActiCrawler(BaseCrawler):
    """
    ACTI网站爬虫，继承自BaseCrawler
    """

    def __init__(self, data_dir="data"):
        """
        初始化ACTI爬虫
        """
        # 调用父类初始化方法
        super().__init__(brand_name="acti", data_dir=data_dir)

        # 设置ACTI特定的属性
        self.base_url = "https://www.acti.com"

        # 设置起始URL
        self.start_urls = ["https://www.acti.com"]

        self.logger.info("ACTI爬虫初始化完成")

    def get_selector(self, url):
        """
        使用requests和Parsel获取页面内容

        Args:
            url: 要获取的URL

        Returns:
            Selector对象
        """
        try:
            resp = requests.get(url, timeout=20)
            resp.raise_for_status()
            selector = Selector(text=resp.text)
            return selector
        except Exception as e:
            self.logger.error(f"获取页面内容时出错 {url}: {str(e)}")
            return None

    def get_links_from_page(self, url, selector=None):
        """
        从页面获取产品链接

        Args:
            url: 页面URL
            selector: 可选的选择器，如果为None则会调用get_selector获取

        Returns:
            产品链接列表
        """
        self.logger.info(f"从页面获取产品链接: {url}")

        # 如果没有提供选择器，则获取一个
        if selector is None:
            selector = self.get_selector(url)

        if not selector:
            return []

        # 获取第二个.carousel-container
        carousel_containers = selector.css('.carousel-container')
        if len(carousel_containers) < 2:
            self.logger.warning("找不到第二个.carousel-container")
            return []

        # 获取第二个carousel-container
        second_carousel = carousel_containers[1]

        # 在其下找到div.card_links > div > a，获取href属性
        product_links = []
        links = second_carousel.css('div.card_links > div > a')

        for link in links:
            href = link.attrib.get('href')
            if href:
                # 如果是相对URL，拼接成完整URL
                if not href.startswith(('http://', 'https://')):
                    href = urljoin(self.base_url, href)
                product_links.append(href)

        self.logger.info(f"找到 {len(product_links)} 个产品链接")
        return product_links

    def process_category_page(self, url):
        """
        处理类别页面

        Args:
            url: 类别页面URL

        Returns:
            产品链接列表
        """
        self.logger.info(f"处理类别页面: {url}")
        return self.get_links_from_page(url)

    def extract_product_details(self, url):
        """
        从ACTI产品页面提取产品详情

        Args:
            url: 产品页面URL

        Returns:
            产品数据字典或None（如果提取失败）
        """
        try:
            # 拼接规格参数URL
            spec_url = f"{url}?tab=specifications"
            self.logger.info(f"访问规格参数页面: {spec_url}")

            # 使用selenium访问
            self.driver.get(spec_url)
            time.sleep(2)  # 等待页面加载

            # 获取product_id (span#selfModelName的text)
            try:
                product_id_element = self.wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "span#selfModelName"))
                )
                product_id = product_id_element.text.strip()
                self.logger.debug(f"获取到产品ID: {product_id}")
            except (TimeoutException, NoSuchElementException) as e:
                self.logger.error(f"无法获取产品ID: {str(e)}")
                return None

            # 获取产品名称 (可能需要根据实际HTML结构调整选择器)
            try:
                name_element = self.driver.find_element(By.CSS_SELECTOR, "div#popupHeaderSpec")
                product_name = name_element.text.strip()
                self.logger.debug(f"获取到产品名称: {product_name}")
            except (TimeoutException, NoSuchElementException) as e:
                self.logger.warning(f"无法获取产品名称: {str(e)}")
                product_name = "未知名称"

            # 提取规格参数
            params = []
            try:
                param_rows = self.driver.find_elements(By.CSS_SELECTOR, "table.c-table > tbody > tr")
                for row in param_rows:
                    try:
                        cells = row.find_elements(By.TAG_NAME, "td")
                        if len(cells) >= 2:
                            param_name = cells[0].text.strip()
                            param_value = cells[1].text.strip()
                            if param_name and param_value:
                                params.append({
                                    "paramName": param_name,
                                    "param": param_value
                                })
                    except Exception as e:
                        self.logger.warning(f"解析参数行时出错: {str(e)}")

                self.logger.debug(f"提取到 {len(params)} 个参数")
            except Exception as e:
                self.logger.warning(f"提取规格参数时出错: {str(e)}")

            # 构建并返回产品数据
            product_data = {
                'product_id': product_id,
                'product_name': product_name,
                'params': params
            }

            return product_data

        except Exception as e:
            self.logger.error(f"提取产品详情时出错: {str(e)}")
            return None
