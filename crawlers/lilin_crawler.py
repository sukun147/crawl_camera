import requests
from urllib.parse import urljoin
from parsel import Selector

from .base_crawler import BaseCrawler


class LilinCrawler(BaseCrawler):
    """
    梅力光电网站爬虫，继承自BaseCrawler
    """

    def __init__(self, data_dir="data"):
        """
        初始化梅力光电爬虫

        Args:
            data_dir: 数据保存目录
        """
        # 调用父类初始化方法，设置use_selenium=False不使用Selenium
        super().__init__(brand_name="meritlilin", data_dir=data_dir, use_selenium=False)

        # 设置基础URL
        self.base_url = "https://www.meritlilin.com"

        # 设置起始URL
        self.start_urls = ["https://www.meritlilin.com/index.php"]

        self.logger.info("梅力光电爬虫初始化完成")

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

        # 获取子分类页面中的产品链接
        product_links = selector.css('div.pic > a::attr(href)').getall()
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

            # 获取product_id（URL最后一个斜杠后的字符串）
            product_id = url.rstrip('/').split('/')[-1]

            # 获取产品名称
            product_name = selector.css('h2.red::text').get('').strip()
            if not product_name:
                self.logger.warning(f"无法获取产品名称 {url}")
                product_name = "未知名称"

            # 获取参数表格
            params = []
            first_tbody = selector.css('tbody')[0] if selector.css('tbody') else None

            if first_tbody:
                rows = first_tbody.css('tr')
                for row in rows:
                    cols = row.css('td')
                    if len(cols) >= 2:
                        param_name = cols[0].css('::text').get('').strip()
                        param_value = cols[1].css('::text').get('').strip()
                        if param_name:
                            params.append({
                                "paramName": param_name,
                                "param": param_value
                            })
                            self.logger.debug(f"提取参数: {param_name} = {param_value}")

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
            self.logger.info(f"处理首页: {url}")

            # 获取首页
            selector = self.get_selector(url)
            if not selector:
                return []

            # 获取所有分类页面链接
            category_links = []

            # 获取第2、3、4个ul.secondsubmenu
            submenus = selector.css('ul.secondsubmenu')[1:4]  # 索引1,2,3对应第2,3,4个元素

            for submenu in submenus:
                # 获取ul下的所有li > a的href属性
                links = submenu.css('li > a::attr(href)').getall()
                for link in links:
                    full_url = urljoin(self.base_url, link)
                    if full_url not in category_links:
                        category_links.append(full_url)
                        self.logger.debug(f"添加分类页面链接: {full_url}")

            self.logger.info(f"找到 {len(category_links)} 个分类页面")

            # 处理所有分类页面和子分类页面
            all_product_links = []
            subcategory_links = []

            # 依次处理每个分类页面
            for category_link in category_links:
                self.logger.info(f"处理分类页面: {category_link}")

                category_selector = self.get_selector(category_link)
                if not category_selector:
                    continue

                # 检查是否有子分类
                subcategory_elements = category_selector.css('div.containerToMix > div a')

                if subcategory_elements:
                    # 有子分类，获取所有子分类链接
                    for element in subcategory_elements:
                        href = element.attrib.get('href', '')
                        if href:
                            full_url = urljoin(self.base_url, href)
                            if full_url not in subcategory_links:
                                subcategory_links.append(full_url)
                                self.logger.debug(f"添加子分类页面链接: {full_url}")
                else:
                    # 没有子分类，当前页面即为子分类页面
                    subcategory_links.append(category_link)

            self.logger.info(f"找到 {len(subcategory_links)} 个子分类页面")

            # 处理所有子分类页面
            for subcategory_link in subcategory_links:
                self.logger.info(f"处理子分类页面: {subcategory_link}")

                product_links = self.get_links_from_page(subcategory_link)
                all_product_links.extend(product_links)
                self.logger.info(f"在子分类 {subcategory_link} 中找到 {len(product_links)} 个产品链接")

            self.logger.info(f"总共找到 {len(all_product_links)} 个产品链接")
            return all_product_links

        except Exception as e:
            self.logger.error(f"处理类别页面时出错 {url}: {str(e)}")
            return []
