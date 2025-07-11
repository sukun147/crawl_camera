import time

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
            "https://www.dahuatech.com/product/lists/14.html",
            "https://www.dahuatech.com/product/lists/19.html",
            "https://www.dahuatech.com/product/lists/1467.html"
        ]

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
                    print(f"产品ID或名称为空 {url}")
                    return None
            except (TimeoutException, NoSuchElementException) as e:
                print(f"无法获取产品ID或名称 {url}: {str(e)}")
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
                print(f"常规点击规格参数按钮失败 {url}: {str(e)}")
                # 尝试JavaScript点击
                try:
                    spec_tab = self.driver.find_element(By.CSS_SELECTOR, "li[data-id=\"2\"]")
                    self.driver.execute_script("arguments[0].click();", spec_tab)
                    time.sleep(1.5)
                except Exception as js_e:
                    print(f"JavaScript点击规格参数按钮失败 {url}: {str(js_e)}")
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
                            print(f"提取参数项时出错 {url}: {str(param_e)}")
                            continue

                # 检查是否提取到参数
                if not params:
                    print(f"未提取到任何规格参数 {url}")
                    return None

            except Exception as e:
                print(f"提取规格参数时出错 {url}: {str(e)}")
                return None

            # 准备产品数据（新格式）
            product_data = {
                'product_id': product_id,
                'product_name': name,
                'params': params
            }

            print(f"✓ 成功提取产品信息: {name} ({product_id})")
            return product_data

        except Exception as e:
            print(f"提取产品详情时出错 {url}: {str(e)}")
            return None

    def process_category_page(self, url):
        """
        处理大华类别页面并处理分页

        Args:
            url: 类别页面URL

        Returns:
            该类别下所有产品链接的列表
        """
        all_product_links = []
        current_url = url
        page_count = 1

        while True:
            print(f"正在处理第 {page_count} 页: {current_url}")

            # 获取当前页面的产品链接
            product_links = self.get_links_from_page(current_url, ".product-list-b > ul > li > p > a")
            all_product_links.extend(product_links)

            print(f"在当前页面找到 {len(product_links)} 个产品链接")

            # 检查是否有下一页
            try:
                self.driver.get(current_url)
                time.sleep(1)

                next_button = self.driver.find_elements(By.CSS_SELECTOR, ".next.btns")

                if next_button and len(next_button) > 0 and "disabled" not in next_button[0].get_attribute("class"):
                    # 点击下一页按钮
                    next_button[0].click()
                    time.sleep(2)
                    current_url = self.driver.current_url
                    page_count += 1
                else:
                    print("没有找到下一页按钮或已到最后一页")
                    break
            except Exception as e:
                print(f"检查下一页时出错: {str(e)}")
                break

        print(f"类别 {url} 共找到 {len(all_product_links)} 个产品链接")
        return all_product_links


if __name__ == "__main__":
    # 创建爬虫实例并运行
    data_dir = "data"  # 默认数据目录
    crawler = DahuaCrawler(data_dir=data_dir)
    crawler.run()
