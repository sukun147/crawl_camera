import time
from urllib.parse import urljoin

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import requests
from parsel import Selector

from .base_crawler import BaseCrawler


class AVerCrawler(BaseCrawler):
    """
    AVer网站爬虫，继承自BaseCrawler
    """

    def __init__(self, data_dir="data"):
        """
        初始化AVer爬虫

        Args:
            data_dir: 数据保存目录
        """
        # 调用父类初始化方法，启用Selenium
        super().__init__(brand_name="aver", data_dir=data_dir)

        # 设置基础URL
        self.base_url = "https://tw.presentation.aver.com"

        # 设置起始URL
        self.start_urls = [
            "https://tw.presentation.aver.com/lines/pro-av",
            "https://tw.presentation.aver.com/lines/visualizers"
        ]

        self.logger.info("AVer爬虫初始化完成")

    def get_selector(self, url):
        """
        使用requests获取页面的Selector对象

        Args:
            url: 要获取的页面URL

        Returns:
            Selector对象，失败则返回None
        """
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            self.logger.info(f"成功获取页面: {url}")
            return Selector(text=response.text)
        except Exception as e:
            self.logger.error(f"获取页面内容时出错 {url}: {str(e)}")
            return None

    def get_links_from_page(self, url, selector=None):
        """
        从页面获取所有.productlist-item > a的href属性

        Args:
            url: 要获取链接的页面URL
            selector: CSS选择器（可选）

        Returns:
            产品链接列表
        """
        links = []

        if not selector:
            selector = self.get_selector(url)

        if not selector:
            self.logger.warning(f"无法获取页面选择器: {url}")
            return links

        # 获取所有.productlist-item > a的href属性
        product_items = selector.css('.productlist-item > a::attr(href)').getall()

        for href in product_items:
            if href:
                # 拼接完整URL
                full_url = urljoin(self.base_url, href)
                if full_url not in links:
                    links.append(full_url)
                    self.logger.debug(f"添加产品链接: {full_url}")

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
            time.sleep(3)  # 等待页面加载

            # 获取product_id (div.prodTxt > h1的text)
            try:
                product_id_elem = self.wait.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, 'div.prodTxt > h1')
                ))
                product_id = product_id_elem.text.strip()
                if not product_id:
                    self.logger.warning(f"无法获取产品ID，跳过产品 {url}")
                    return None
            except (TimeoutException, NoSuchElementException) as e:
                self.logger.warning(f"无法获取产品ID，跳过产品 {url}: {str(e)}")
                return None

            # 获取产品名称 (div.prodTxt > h2的text)
            try:
                product_name_elem = self.driver.find_element(By.CSS_SELECTOR, 'div.prodTxt > h2')
                product_name = product_name_elem.text.strip()
                if not product_name:
                    product_name = "未知名称"
            except NoSuchElementException as e:
                self.logger.error(f"无法获取产品名称 {url}: {str(e)}")
                product_name = "未知名称"

            # 查找spec-btn按钮
            try:
                spec_button = self.wait.until(EC.presence_of_element_located(
                    (By.CSS_SELECTOR, 'button.spec-btn')
                ))

                # 滚动到按钮位置
                self.driver.execute_script("arguments[0].scrollIntoView(true);", spec_button)
                time.sleep(1)

                # 直接使用JavaScript点击
                self.driver.execute_script("arguments[0].click();", spec_button)

                time.sleep(2)  # 等待规格内容加载

            except Exception as e:
                self.logger.warning(f"点击规格按钮失败 {url}: {str(e)}")

            # 获取参数
            params = []
            try:
                dl_elements = self.driver.find_elements(By.CSS_SELECTOR, 'li.description > dl')

                for dl in dl_elements:
                    try:
                        # 获取dt标签的text作为paramName
                        dt_elem = dl.find_element(By.TAG_NAME, 'dt')
                        param_name = dt_elem.text.strip()

                        # 获取所有dd > ul > li的text
                        li_elements = dl.find_elements(By.CSS_SELECTOR, 'dd > ul > li')
                        param_values = []

                        for li in li_elements:
                            param_value = li.text.strip()
                            if param_value:
                                param_values.append(param_value)

                        # 拼接所有参数值
                        param_value_combined = "; ".join(param_values)

                        if param_name and param_values:
                            params.append({
                                "paramName": param_name,
                                "param": param_value_combined
                            })
                            self.logger.debug(f"提取参数: {param_name} = {param_value_combined}")
                    except Exception as param_e:
                        self.logger.warning(f"提取单个参数时出错: {str(param_e)}")
                        continue

            except Exception as e:
                self.logger.warning(f"获取参数时出错 {url}: {str(e)}")

            # 检查是否获取到规格参数
            if not params:
                self.logger.warning(f"未提取到任何规格参数 {url}")

            # 构建产品数据
            product_data = {
                'product_id': product_id,
                'product_name': product_name,
                'params': params
            }

            return product_data

        except Exception as e:
            self.logger.error(f"提取产品详情时出错 {url}: {str(e)}")
            return None

    def process_category_page(self, url):
        """
        处理类别页面

        Args:
            url: 类别页面URL

        Returns:
            产品链接列表
        """
        self.logger.info(f"处理类别页面: {url}")

        # 获取产品链接
        product_links = self.get_links_from_page(url)

        self.logger.info(f"类别页面 {url} 共找到 {len(product_links)} 个产品链接")
        return product_links
