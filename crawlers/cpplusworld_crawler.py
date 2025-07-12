import requests
from urllib.parse import urljoin
from parsel import Selector

from .base_crawler import BaseCrawler


class CPlusWorldCrawler(BaseCrawler):
    """
    CPlusWorld网站爬虫，继承自BaseCrawler
    """

    def __init__(self, data_dir="data"):
        """
        初始化CPlusWorld爬虫
        """
        # 调用父类初始化方法，设置use_selenium=False不使用Selenium
        super().__init__(brand_name="cplusworld", data_dir=data_dir, use_selenium=False)

        # 设置CPlusWorld特定的属性
        self.base_url = "https://www.cpplusworld.com"

        # 设置起始URL
        self.start_urls = ["https://www.cpplusworld.com/Products/network-camera"]

    def get_selector(self, url):
        """
        获取页面的Selector对象

        Args:
            url: 要获取的页面URL

        Returns:
            Selector对象，失败则返回None
        """
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()  # 如果响应状态码不是200，抛出异常
            return Selector(text=response.text)
        except Exception as e:
            self.logger.error(f"获取页面内容时出错 {url}: {str(e)}")
            return None

    def get_links_from_page(self, url, selector=None):
        """
        获取页面中的链接

        Args:
            url: 要获取链接的页面URL
            selector: CSS选择器（可选）

        Returns:
            链接列表
        """
        links = []
        selector = self.get_selector(url)
        if not selector:
            return links

        content_divs = selector.css('.search-content > div > div')
        self.logger.debug(f"在页面 {url} 找到 {len(content_divs)} 个内容div")

        for div in content_divs:
            h4_with_a = div.css('.section-title > a')
            if h4_with_a:
                # 如果h4下有a标签，获取其href属性
                href = h4_with_a.attrib.get('href')
                if href:
                    full_url = urljoin(self.base_url, href)
                    # 访问这个URL获取商品链接
                    sub_selector = self.get_selector(full_url)
                    if sub_selector:
                        item_image = sub_selector.css('a.item-image')
                        if item_image:
                            for item in item_image:
                                product_url = urljoin(self.base_url, item.attrib.get('href', ''))
                                if product_url and product_url not in links:
                                    links.append(product_url)
                                    self.logger.debug(f"添加产品链接: {product_url}")
            else:
                # 如果h4下没有a标签，直接获取a.item-image的href
                item_image = div.css('a.item-image')
                if item_image and 'href' in item_image.attrib:
                    product_url = urljoin(self.base_url, item_image.attrib['href'])
                    if product_url and product_url not in links:
                        links.append(product_url)
                        self.logger.debug(f"添加产品链接: {product_url}")

        self.logger.info(f"从页面 {url} 共获取到 {len(links)} 个链接")
        return links

    def extract_product_details(self, url):
        """
        从CPlusWorld产品页面提取产品详情

        Args:
            url: 产品页面URL

        Returns:
            产品数据字典或None（如果提取失败）
        """
        selector = self.get_selector(url)
        if not selector:
            return None

        try:
            # 获取产品ID (产品标题)
            product_title = selector.css('.product-title::text').get()
            if not product_title:
                self.logger.warning(f"无法获取产品ID {url}")
                return None
            product_id = product_title.strip()

            # 获取产品名称
            product_name = selector.css('.product-info-header > p::text').get()
            if not product_name:
                self.logger.warning(f"无法获取产品名称 {url}")
                product_name = "未知名称"
            else:
                product_name = product_name.strip()

            # 获取参数表格
            params = []
            table_rows = selector.css('.table-product > tr')
            self.logger.debug(f"找到 {len(table_rows)} 行参数数据")

            for row in table_rows:
                # 获取参数名称和值
                cells = row.css('td')
                if len(cells) >= 2:
                    param_name = cells[0].css('strong::text').get()
                    if param_name:
                        param_name = param_name.strip()
                        param_value = cells[1].css('::text').get('').strip()

                        if param_name and param_value:
                            params.append({
                                "paramName": param_name,
                                "param": param_value
                            })
                            self.logger.debug(f"提取参数: {param_name} = {param_value}")

            # 构建产品数据
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
        处理分类页面，获取所有产品链接

        Args:
            url: 分类页面URL

        Returns:
            产品链接列表
        """
        self.logger.info(f"处理分类页面: {url}")
        links = self.get_links_from_page(url)
        self.logger.info(f"从分类页面 {url} 获取到 {len(links)} 个产品链接")
        return links
