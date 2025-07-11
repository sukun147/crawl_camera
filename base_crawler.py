import json
import os

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager


class BaseCrawler:
    def __init__(self, brand_name, data_dir="data", use_selenium=True):
        """
        初始化爬虫
        :param brand_name: 品牌名称
        :param data_dir: 数据保存目录
        :param use_selenium: 是否使用Selenium（False则不初始化WebDriver）
        """
        self.brand_name = brand_name
        self.data_dir = data_dir
        self.use_selenium = use_selenium

        # 确保数据目录存在
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)

        # 只有在需要使用Selenium时才初始化WebDriver
        if self.use_selenium:
            self._initialize_webdriver()

        # 基础URL和起始URL（子类应覆盖这些属性）
        self.base_url = ""
        self.start_urls = []

    def _initialize_webdriver(self):
        """初始化WebDriver（仅在use_selenium=True时调用）"""
        # 设置Chrome选项
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # 无头模式
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")

        # 初始化WebDriver
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.wait = WebDriverWait(self.driver, 10)  # 10秒等待时间

    def get_links_from_page(self, url, selector=None):
        """获取页面中的链接（子类应覆盖此方法）"""
        raise NotImplementedError("子类必须实现get_links_from_page方法")

    def extract_product_details(self, url):
        """从产品页面提取产品详情（子类必须实现）"""
        raise NotImplementedError("子类必须实现extract_product_details方法")

    def process_category_page(self, url):
        """处理类别页面（子类应覆盖此方法）"""
        raise NotImplementedError("子类必须实现process_category_page方法")

    def process_and_save_data(self, products):
        """处理并保存产品数据"""
        if not products:
            print("没有产品数据可保存")
            return

        # 保存为JSON文件
        json_path = os.path.join(self.data_dir, f"{self.brand_name}.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(products, f, ensure_ascii=False, indent=4)
        print(f"JSON数据已保存至: {json_path}")

    def run(self):
        """运行爬虫"""
        print(f"开始爬取 {self.brand_name} 产品数据...")

        all_products = []
        for start_url in self.start_urls:
            # 获取产品链接
            product_links = self.process_category_page(start_url)

            # 爬取每个产品页面
            for link in product_links:
                product_data = self.extract_product_details(link)
                if product_data:
                    all_products.append(product_data)
                    print(f"成功爬取产品: {product_data.get('product_id', 'unknown')} - {product_data.get('product_name', 'unknown')}")

        # 保存数据
        if all_products:
            print(f"总共爬取了 {len(all_products)} 个产品")
            self.process_and_save_data(all_products)
        else:
            print("未爬取到任何产品数据")

        # 关闭WebDriver（如果已初始化）
        self.close()

        print(f"{self.brand_name} 爬虫任务完成!")

    def close(self):
        """关闭爬虫，释放资源"""
        if self.use_selenium and hasattr(self, 'driver'):
            self.driver.quit()
            print("WebDriver已关闭")
