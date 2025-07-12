import json
import os
import logging
import sys
from abc import ABC, abstractmethod

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager


class BaseCrawler(ABC):
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
        self._ensure_dir_exists(data_dir)

        # 设置日志
        self.logger = self._setup_logger()

        # 只有在需要使用Selenium时才初始化WebDriver
        if self.use_selenium:
            self._initialize_webdriver()

        # 基础URL和起始URL（子类应覆盖这些属性）
        self.base_url = ""
        self.start_urls = []

    def _ensure_dir_exists(self, directory):
        """确保目录存在，如果不存在则创建"""
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"创建目录: {directory}")

    def _setup_logger(self):
        """设置日志记录器，使用UTF-8编码"""
        logger = logging.getLogger(f"{self.brand_name}_crawler")
        logger.setLevel(logging.INFO)

        # 如果logger已经有处理器，不再添加新的处理器
        if logger.handlers:
            return logger

        # 创建控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)

        # 创建格式化器
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)

        # 添加控制台处理器
        logger.addHandler(console_handler)

        # 创建文件处理器
        log_dir = "logs"
        self._ensure_dir_exists(log_dir)

        log_file_path = os.path.join(log_dir, f"{self.brand_name}.log")
        file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.info(f"日志将保存到: {log_file_path}")

        return logger

    def _initialize_webdriver(self):
        """初始化WebDriver（仅在use_selenium=True时调用）"""
        # 设置Chrome选项
        chrome_options = Options()
        # chrome_options.add_argument("--headless")  # 无头模式
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")

        try:
            # 初始化WebDriver
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.wait = WebDriverWait(self.driver, 10)  # 10秒等待时间
            self.logger.info("WebDriver初始化成功")
        except Exception as e:
            self.logger.error(f"WebDriver初始化失败: {str(e)}")
            raise

    @abstractmethod
    def get_links_from_page(self, url, selector=None):
        """获取页面中的链接（子类必须实现）"""
        pass

    @abstractmethod
    def extract_product_details(self, url):
        """从产品页面提取产品详情（子类必须实现）"""
        pass

    @abstractmethod
    def process_category_page(self, url):
        """处理类别页面（子类必须实现）"""
        pass

    def process_and_save_data(self, products):
        """处理并保存产品数据"""
        if not products:
            self.logger.warning("没有产品数据可保存")
            return

        # 保存为JSON文件
        json_path = os.path.join(self.data_dir, f"{self.brand_name}.json")
        try:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(products, f, ensure_ascii=False, indent=4)
            self.logger.info(f"JSON数据已保存至: {json_path}")
        except Exception as e:
            self.logger.error(f"保存JSON数据到 {json_path} 时出错: {str(e)}")

    def run(self):
        """运行爬虫"""
        self.logger.info(f"开始爬取 {self.brand_name} 产品数据...")

        all_products = []
        for start_url in self.start_urls:
            # 获取产品链接
            self.logger.info(f"处理类别页面: {start_url}")
            product_links = self.process_category_page(start_url)
            self.logger.info(f"找到 {len(product_links)} 个产品链接")

            # 爬取每个产品页面
            for link in product_links:
                self.logger.info(f"提取产品详情: {link}")
                product_data = self.extract_product_details(link)
                if product_data:
                    all_products.append(product_data)
                    self.logger.info(f"成功提取产品: {product_data.get('product_id', 'unknown')}")
                else:
                    self.logger.warning(f"提取产品详情失败: {link}")

        # 保存数据
        self.process_and_save_data(all_products)
        self.logger.info(f"爬取完成，共获取 {len(all_products)} 个产品数据")

        # 如果使用了Selenium，关闭WebDriver
        if self.use_selenium and hasattr(self, 'driver'):
            self.driver.quit()
            self.logger.info("WebDriver已关闭")
