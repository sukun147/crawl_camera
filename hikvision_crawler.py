import time
from urllib.parse import urljoin

import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager


class HikvisionCrawler:
    def __init__(self):
        # 设置Chrome选项
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # 无界面模式
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

        # 初始化WebDriver
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        self.wait = WebDriverWait(self.driver, 10)

        # 数据存储
        self.all_products = []

        # 基础URL
        self.base_url = "https://www.hikvision.com"

    def close(self):
        """关闭WebDriver"""
        if self.driver:
            self.driver.quit()

    def get_links_from_page(self, url, selector):
        """获取页面中匹配选择器的所有链接"""
        links = []
        try:
            self.driver.get(url)
            time.sleep(2)  # 等待页面加载

            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
            for element in elements:
                href = element.get_attribute('href')
                if href:
                    # 处理相对URL
                    if not href.startswith(('http://', 'https://')):
                        href = urljoin(self.base_url, href)
                    links.append(href)
                else:
                    # 如果href为空，尝试获取onclick属性
                    onclick = element.get_attribute('onclick')
                    if onclick and "window.location" in onclick:
                        # 从onclick属性中提取URL
                        try:
                            url_in_onclick = onclick.split("'")[1]
                            if not url_in_onclick.startswith(('http://', 'https://')):
                                url_in_onclick = urljoin(self.base_url, url_in_onclick)
                            links.append(url_in_onclick)
                        except:
                            pass

            return links
        except Exception as e:
            print(f"获取链接时出错 {url}: {str(e)}")
            return []

    def extract_product_details(self, url):
        """从产品页面提取产品详情"""
        try:
            self.driver.get(url)
            time.sleep(2)  # 等待页面加载

            # 获取产品名称和ID
            name_element = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".modelName > span")))
            name = name_element.text.strip()

            id_element = self.driver.find_element(By.CSS_SELECTOR, ".model > span")
            product_id = id_element.text.strip()

            # 获取规格参数
            specs = {}
            spec_elements = self.driver.find_elements(By.CSS_SELECTOR, ".tech-specs-accordion-content-desc ul")

            for ul in spec_elements:
                li_elements = ul.find_elements(By.TAG_NAME, "li")
                # 从第二个li元素开始，按照要求
                for li in li_elements[1:]:
                    try:
                        spans = li.find_elements(By.TAG_NAME, "span")
                        if len(spans) >= 2:
                            param_name = spans[0].text.strip()
                            param_value = spans[1].text.strip()
                            specs[param_name] = param_value
                    except Exception as e:
                        print(f"提取参数时出错 {url}: {str(e)}")

            # 准备产品数据
            product_data = {
                'name': name,
                'id': product_id,
                'url': url,
                'specifications': specs
            }

            return product_data

        except Exception as e:
            print(f"提取产品详情时出错 {url}: {str(e)}")
            return None

    def process_product_page_with_pagination(self, url):
        """处理带分页的产品页面"""
        products = []

        # 处理第一页
        product_links = self.get_links_from_page(url, ".btn-details-link")
        for link in product_links:
            product_data = self.extract_product_details(link)
            if product_data:
                products.append(product_data)
                print(f"已提取产品: {product_data['name']} ({product_data['id']})")

        # 检查分页
        try:
            self.driver.get(url)
            pagination_elements = self.driver.find_elements(By.CSS_SELECTOR, ".paginationjs-pages > ul > li")

            # 如果有分页并且元素数量大于2（排除第一个和最后一个）
            if len(pagination_elements) > 2:
                # 从第2页（索引1）开始，排除最后一个元素
                for page_idx in range(1, len(pagination_elements) - 1):
                    try:
                        # 返回列表页
                        self.driver.get(url)
                        time.sleep(2)

                        # 找到并点击分页元素
                        pagination_elements = self.driver.find_elements(By.CSS_SELECTOR,
                                                                        ".paginationjs-pages > ul > li")
                        page_element = pagination_elements[page_idx + 1]  # +1因为我们从第二页开始
                        page_element.click()
                        time.sleep(3)  # 点击后等待页面加载

                        # 获取新页面中的产品链接
                        product_links = self.get_links_from_page(self.driver.current_url, ".btn-details-link")
                        for link in product_links:
                            product_data = self.extract_product_details(link)
                            if product_data:
                                products.append(product_data)
                                print(f"已提取产品: {product_data['name']} ({product_data['id']})")

                    except Exception as e:
                        print(f"处理分页 {page_idx + 1} 时出错 {url}: {str(e)}")

        except Exception as e:
            print(f"检查分页时出错 {url}: {str(e)}")

        return products

    def run(self):
        """运行爬虫"""
        try:
            # 步骤1：从主页获取所有tile-card链接
            main_url = "https://www.hikvision.com/cn/products/front-end-product/"
            category_links = self.get_links_from_page(main_url, ".tile-card")
            print(f"在主页上找到 {len(category_links)} 个类别链接")

            # 步骤2：从每个类别页面获取所有tile-card链接
            subcategory_links = []
            for link in category_links:
                sub_links = self.get_links_from_page(link, ".tile-card")
                subcategory_links.extend(sub_links)
                print(f"从 {link} 找到 {len(sub_links)} 个子类别链接")

            print(f"子类别链接总数: {len(subcategory_links)}")

            # 步骤3、4、5：处理每个带分页的子类别页面
            for link in subcategory_links:
                print(f"处理子类别页面: {link}")
                products = self.process_product_page_with_pagination(link)
                self.all_products.extend(products)
                print(f"目前找到的产品总数: {len(self.all_products)}")

            # 保存结果到CSV
            self.save_to_csv()

            print(f"爬取完成。产品总数: {len(self.all_products)}")

        except Exception as e:
            print(f"运行爬虫时出错: {str(e)}")

        finally:
            self.close()

    def save_to_csv(self):
        """保存产品数据到CSV文件"""
        try:
            # 准备基本产品信息数据
            basic_data = []
            for product in self.all_products:
                basic_data.append({
                    'name': product['name'],
                    'id': product['id'],
                    'url': product['url']
                })

            # 保存基本产品信息
            basic_df = pd.DataFrame(basic_data)
            basic_df.to_csv('data/hikvision_products.csv', index=False, encoding='utf-8-sig')

            # 准备规格参数数据（展平规格参数）
            specs_data = []
            for product in self.all_products:
                for param_name, param_value in product['specifications'].items():
                    specs_data.append({
                        'product_id': product['id'],
                        'param_name': param_name,
                        'param_value': param_value
                    })

            # 保存规格参数
            specs_df = pd.DataFrame(specs_data)
            specs_df.to_csv('data/hikvision_specifications.csv', index=False, encoding='utf-8-sig')

            print("数据已保存到CSV文件: data/hikvision_products.csv 和 data/hikvision_specifications.csv")

        except Exception as e:
            print(f"保存数据到CSV时出错: {str(e)}")


if __name__ == "__main__":
    crawler = HikvisionCrawler()
    crawler.run()
