import requests
from urllib.parse import urljoin
from parsel import Selector

from .base_crawler import BaseCrawler


class GeoVisionCrawler(BaseCrawler):
    """
    GeoVision网站爬虫，继承自BaseCrawler
    """

    def __init__(self, data_dir="data"):
        """
        初始化GeoVision爬虫

        Args:
            data_dir: 数据保存目录
        """
        # 调用父类初始化方法，设置use_selenium=False不使用Selenium
        super().__init__(brand_name="geovision", data_dir=data_dir, use_selenium=False)

        # 设置基础URL
        self.base_url = "https://www.geovision.com.tw"

        # 设置起始URL
        self.start_urls = ["https://www.geovision.com.tw/products.php?c1=3"]

        self.logger.info("GeoVision爬虫初始化完成")

    def get_selector(self, url):
        """
        获取页面的Selector对象

        Args:
            url: 页面URL

        Returns:
            Selector对象，如果请求失败则返回None
        """
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()  # 如果响应状态码不是200，抛出异常
            return Selector(text=response.text)
        except Exception as e:
            self.logger.error(f"获取页面内容时出错 {url}: {str(e)}")
            return None

    def get_links_from_page(self, url, selector=None):
        """
        获取页面中的链接

        Args:
            url: 页面URL
            selector: 页面的Selector对象，如果为None则重新获取

        Returns:
            链接列表
        """
        if not selector:
            selector = self.get_selector(url)

        if not selector:
            return []

        links = []

        # 获取所有a.box的href属性
        product_links = selector.css('a.box::attr(href)').getall()
        for link in product_links:
            full_url = urljoin(self.base_url, link)
            if full_url not in links:
                links.append(full_url)
                self.logger.debug(f"添加产品链接: {full_url}")

        return links

    def extract_product_details(self, url):
        """
        从产品页面提取产品详情

        Args:
            url: 产品页面URL

        Returns:
            产品详情字典，如果提取失败则返回None
        """
        try:
            selector = self.get_selector(url)
            if not selector:
                return None

            # 获取product_id（div.textWrapper > h1的text）
            product_id = selector.css('div.textWrapper > h1::text').get('').strip()
            if not product_id:
                self.logger.warning(f"无法获取产品ID {url}")
                return None

            # 获取产品名称（p.intro的text）
            product_name = selector.css('p.intro::text').get('').strip()
            if not product_name:
                self.logger.warning(f"无法获取产品名称 {url}")
                product_name = "未知名称"

            # 获取参数列表（div.proDetailHtml > ul > li）
            params = []
            param_items = selector.css('div.proDetailHtml > ul > li::text').getall()

            for i, param_text in enumerate(param_items):
                param_text = param_text.strip()
                if param_text:
                    params.append({
                        "paramName": f"参数{i + 1}",  # 由于只有单一文本，使用索引作为参数名
                        "param": param_text
                    })
                    self.logger.debug(f"提取参数: 参数{i + 1} = {param_text}")

            # 检查是否获取到规格参数
            if not params:
                self.logger.warning(f"未提取到任何规格参数 {url}")

            product_data = {
                'product_id': product_id,
                'product_name': product_name,
                'params': params
            }

            self.logger.info(f"成功提取产品信息: {product_name} ({product_id})")
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
        try:
            self.logger.info(f"处理类别页面: {url}")

            # 直接获取产品链接
            selector = self.get_selector(url)
            if not selector:
                return []

            product_links = self.get_links_from_page(url, selector)

            self.logger.info(f"类别页面 {url} 共找到 {len(product_links)} 个产品链接")
            return product_links

        except Exception as e:
            self.logger.error(f"处理类别页面时出错 {url}: {str(e)}")
            return []
