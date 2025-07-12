import time
import requests
from urllib.parse import urljoin
from parsel import Selector

from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from base_crawler import BaseCrawler


class DahuaCrawler(BaseCrawler):
    """
    大华网站爬虫，继承自BaseCrawler
    """

    def __init__(self, data_dir="data"):
        """
        初始化大华爬虫
        """
        # 调用父类初始化方法
        super().__init__(brand_name="dahua", data_dir=data_dir)

        # 设置大华特定的属性
        self.base_url = "https://www.dahuatech.com"

        # 设置起始页面列表
        self.start_urls = [
            "https://www.dahuatech.com/product/lists/14",
            "https://www.dahuatech.com/product/lists/19",
            "https://www.dahuatech.com/product/lists/1467",
            "https://www.dahuatech.com/product/lists/1491",
            "https://www.dahuatech.com/product/lists/1492"
        ]

    def get_selector(self, url):
        """
        使用requests获取页面的Selector对象

        Args:
            url: 要获取内容的URL

        Returns:
            Selector对象，失败则返回None
        """
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return Selector(text=response.text)
        except Exception as e:
            self.logger.error(f"获取页面内容时出错 {url}: {str(e)}")
            return None

    def get_links_from_page(self, url, selector=None):
        """
        从页面获取链接，使用requests而非selenium

        Args:
            url: 页面URL
            selector: CSS选择器，默认为.product-list-b > ul > li > p > a

        Returns:
            链接列表
        """
        if selector is None:
            selector = ".product-list-b > ul > li > p > a"

        try:
            page_selector = self.get_selector(url)
            if not page_selector:
                return []

            links = []
            elements = page_selector.css(selector)

            for element in elements:
                href = element.attrib.get('href')
                if href:
                    # 处理相对URL
                    full_url = urljoin(self.base_url, href)
                    links.append(full_url)

            self.logger.debug(f"从页面 {url} 获取到 {len(links)} 个链接")
            return links
        except Exception as e:
            self.logger.error(f"获取链接时出错 {url}: {str(e)}")
            return []

    def extract_product_details(self, url):
        """
        从大华产品页面提取产品详情

        Args:
            url: 产品页面URL

        Returns:
            产品数据字典或None（如果提取失败）
        """
        try:
            self.driver.get(url)
            time.sleep(2)  # 等待页面加载

            # 获取产品ID和名称
            try:
                id_element = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".info-font.fr > h2")))
                product_id = id_element.text.strip()

                name_element = self.driver.find_element(By.CSS_SELECTOR, ".info-font.fr > h3")
                name = name_element.text.strip()

                if not product_id or not name:
                    self.logger.warning(f"产品ID或名称为空 {url}")
                    return None
            except (TimeoutException, NoSuchElementException) as e:
                self.logger.error(f"无法获取产品ID或名称 {url}: {str(e)}")
                return None

            # 点击规格参数按钮 - 使用li[data-id="2"]选择器
            try:
                # 首先尝试等待元素可点击
                spec_tab = self.wait.until(EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "li[data-id=\"2\"]")
                ))
                # 尝试常规点击
                spec_tab.click()
                time.sleep(1.5)  # 延长等待时间，确保参数加载
            except (TimeoutException, NoSuchElementException, ElementClickInterceptedException) as e:
                self.logger.warning(f"常规点击规格参数按钮失败 {url}: {str(e)}")
                # 尝试JavaScript点击
                try:
                    spec_tab = self.driver.find_element(By.CSS_SELECTOR, "li[data-id=\"2\"]")
                    self.driver.execute_script("arguments[0].click();", spec_tab)
                    time.sleep(1.5)
                except Exception as js_e:
                    self.logger.warning(f"JavaScript点击规格参数按钮失败 {url}: {str(js_e)}")
                    # 如果还是不行，继续但可能无法获取参数

            # 获取规格参数
            params = []
            try:
                parameter_sections = self.driver.find_elements(By.CSS_SELECTOR, ".parameter-info")

                for section in parameter_sections:
                    # 从第二个parameter-item开始获取
                    parameter_items = section.find_elements(By.CSS_SELECTOR, ".parameter-item")

                    for item in parameter_items[1:]:  # 跳过第一个
                        try:
                            label_element = item.find_element(By.CSS_SELECTOR, ".parameter-label")
                            value_element = item.find_element(By.CSS_SELECTOR, ".parameter-value")

                            param_name = label_element.text.strip()
                            param_value = value_element.text.strip()

                            if param_name and param_value:  # 确保参数名和值不为空
                                params.append({
                                    "paramName": param_name,
                                    "param": param_value
                                })
                        except Exception as param_e:
                            self.logger.debug(f"提取参数项时出错: {str(param_e)}")
                            continue

                # 检查是否提取到参数
                if not params:
                    self.logger.warning(f"未提取到任何规格参数 {url}")
                    return None

            except Exception as e:
                self.logger.error(f"提取规格参数时出错 {url}: {str(e)}")
                return None

            # 准备产品数据
            product_data = {
                'product_id': product_id,
                'product_name': name,
                'params': params
            }

            self.logger.info(f"成功提取产品信息: {name} ({product_id})")
            return product_data

        except Exception as e:
            self.logger.error(f"提取产品详情时出错 {url}: {str(e)}")
            return None

    def process_category_page(self, url):
        """
        处理大华类别页面并处理分页，使用requests获取页面内容

        Args:
            url: 类别页面URL

        Returns:
            该类别下所有产品链接的列表
        """
        all_product_links = []

        # 获取首页内容
        self.logger.info(f"处理类别页面: {url}")
        selector = self.get_selector(url)
        if not selector:
            self.logger.error(f"无法获取类别页面内容: {url}")
            return all_product_links

        # 获取第一页的产品链接
        product_links = self.get_links_from_page(url)
        all_product_links.extend(product_links)
        self.logger.info(f"在第1页找到 {len(product_links)} 个产品链接")

        # 检查是否存在分页
        pagination = selector.css('div.news-page')
        if not pagination:
            self.logger.info(f"类别页面 {url} 没有分页")
            return all_product_links

        # 获取总页数
        try:
            # 找到分页中倒数第二个a标签
            page_links = pagination.css('a')
            if len(page_links) >= 2:
                total_pages = int(page_links[-2].css('::text').get('').strip())
                self.logger.info(f"类别页面 {url} 共有 {total_pages} 页")
            else:
                self.logger.info(f"类别页面 {url} 只有一页")
                return all_product_links
        except Exception as e:
            self.logger.error(f"获取总页数出错: {str(e)}")
            return all_product_links

        # 处理后续页面
        for page in range(2, total_pages + 1):
            page_url = f"{url}/{page}.html"
            self.logger.info(f"处理第 {page} 页: {page_url}")

            try:
                page_links = self.get_links_from_page(page_url)
                all_product_links.extend(page_links)
                self.logger.info(f"在第 {page} 页找到 {len(page_links)} 个产品链接")
            except Exception as e:
                self.logger.error(f"处理第 {page} 页时出错: {str(e)}")

        self.logger.info(f"类别 {url} 共找到 {len(all_product_links)} 个产品链接")
        return all_product_links
