import time

import requests
from parsel import Selector
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from .base_crawler import BaseCrawler


class VivotekCrawler(BaseCrawler):
    """
    VIVOTEK网站爬虫，继承自BaseCrawler
    """

    def __init__(self, data_dir="data"):
        """
        初始化VIVOTEK爬虫
        """
        # 调用父类初始化方法
        super().__init__(brand_name="vivotek", data_dir=data_dir)

        # 设置VIVOTEK特定的属性
        self.base_url = "https://www.vivotek.com"

        # 不使用起始URL列表，而是在process_category_page中处理
        self.start_urls = ["https://www.vivotek.com/products/network_cameras"]

    def get_selector(self, url):
        """
        使用requests和Parsel获取页面内容

        Args:
            url: 要获取的URL

        Returns:
            Selector对象
        """
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            selector = Selector(text=resp.text)
            return selector
        except Exception as e:
            self.logger.error(f"获取页面内容时出错 {url}: {str(e)}")
            return None

    def get_links_from_page(self, url, selector=None):
        """
        获取页面中的链接，根据URL类型自动判断是获取分类卡片还是产品链接

        Args:
            url: 页面URL
            selector: 选择器对象，如果为None则会自动获取

        Returns:
            链接列表
        """
        # 如果没有提供selector，则自动获取
        if selector is None:
            selector = self.get_selector(url)
            if not selector:
                self.logger.error(f"无法获取页面选择器 {url}")
                return []

        # 根据URL类型选择不同的链接提取方法
        if url == self.start_urls[0]:
            # 处理主分类页面，获取分类卡片链接
            cards = selector.css("frontend-cards-general > a")
            links = []
            for card in cards:
                href = card.attrib.get("href")
                if href and not href.startswith("http"):
                    href = f"{self.base_url}{href}"
                links.append(href)
            self.logger.info(f"获取到 {len(links)} 个分类卡片链接")
            return links
        else:
            # 处理分类页面，获取产品链接
            prods = selector.css("frontend-product-card > a")
            links = []
            for prod in prods:
                href = prod.attrib.get("href")
                if href and not href.startswith("http"):
                    href = f"{self.base_url}{href}"
                links.append(href)
            self.logger.info(f"从分类页面 {url} 获取到 {len(links)} 个产品链接")
            return links

    def extract_product_details(self, url):
        """
        从VIVOTEK产品页面提取产品详情

        Args:
            url: 产品页面URL

        Returns:
            产品数据字典或None（如果提取失败）
        """
        try:
            # 添加spec标签页到URL
            url_with_tab = url + "?tab=spec"
            self.driver.get(url_with_tab)
            time.sleep(2)  # 等待页面加载

            # 获取产品ID
            try:
                id_elem = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "h1.mt-4")))
                prod_id = id_elem.text.strip()
                if not prod_id:
                    self.logger.warning(f"产品ID为空 {url}")
                    return None
            except (TimeoutException, NoSuchElementException) as e:
                self.logger.error(f"无法获取产品ID {url}: {str(e)}")
                return None

            # 获取产品名称
            try:
                name_elem = self.driver.find_element(By.CSS_SELECTOR, "h3.mt-2")
                prod_name = name_elem.text.strip()
                if not prod_name:
                    self.logger.warning(f"产品名称为空 {url}")
                    return None
            except (TimeoutException, NoSuchElementException) as e:
                self.logger.error(f"无法获取产品名称 {url}: {str(e)}")
                return None

            # 点击规格参数按钮
            try:
                btn = self.driver.find_element(By.CSS_SELECTOR, ".shrink-0 > button:nth-child(1)")
                # 使用JavaScript执行点击，解决无头模式下点击不生效的问题
                self.driver.execute_script("arguments[0].click();", btn)
                time.sleep(2)  # 等待参数加载
            except Exception as e:
                self.logger.warning(f"点击规格按钮时出错 {url}: {str(e)}")
                # 继续尝试获取参数

            # 获取规格参数
            params = []
            try:
                groups = self.driver.find_elements(By.CSS_SELECTOR, "frontend-collapses-general > div > div > div")
                for g in groups:
                    divs = g.find_elements(By.XPATH, "./div")
                    if len(divs) >= 2:
                        param_name = divs[0].text.strip()
                        param_p = []
                        sub_divs = divs[1].find_elements(By.XPATH, "./div")
                        for sub_div in sub_divs:
                            ps = sub_div.find_elements(By.TAG_NAME, "p")
                            for p in ps:
                                if p.text.strip():
                                    param_p.append(p.text.strip())
                        param_value = "; ".join(param_p)
                        if param_name and param_value:
                            params.append({
                                "paramName": param_name,
                                "param": param_value
                            })

                # 检查是否提取到参数
                if not params:
                    self.logger.warning(f"未提取到任何规格参数 {url}")
                    return None

            except Exception as e:
                self.logger.error(f"提取规格参数时出错 {url}: {str(e)}")
                return None

            # 准备产品数据
            product_data = {
                'product_id': prod_id,
                'product_name': prod_name,
                'params': params
            }

            self.logger.info(f"成功提取产品信息: {prod_name} ({prod_id})")
            return product_data

        except Exception as e:
            self.logger.error(f"提取产品详情时出错 {url}: {str(e)}")
            return None

    def process_category_page(self, url):
        """
        处理VIVOTEK类别页面，从分类卡片到产品列表

        Args:
            url: 类别页面URL

        Returns:
            该类别下所有产品链接的列表
        """
        # VIVOTEK有两层结构：先获取分类卡片，再从每个卡片获取产品
        all_product_links = []

        # 获取所有分类卡片
        card_links = self.get_links_from_page(self.start_urls[0])
        self.logger.info(f"共获取到{len(card_links)}个大类页面")

        # 从每个卡片获取产品链接
        for card_link in card_links:
            product_links = self.get_links_from_page(card_link)
            self.logger.info(f"处理大类页面: {card_link}，产品数量: {len(product_links)}")
            all_product_links.extend(product_links)

        self.logger.info(f"所有类别共找到 {len(all_product_links)} 个产品链接")
        return all_product_links
