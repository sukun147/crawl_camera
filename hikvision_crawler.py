import time
from urllib.parse import urljoin

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from base_crawler import BaseCrawler


class HikvisionCrawler(BaseCrawler):
    def __init__(self, data_dir="data"):
        # 调用父类初始化方法
        super().__init__(brand_name="hikvision", data_dir=data_dir)

        # 设置基础URL
        self.base_url = "https://www.hikvision.com"

        # 设置起始URL
        self.start_urls = ["https://www.hikvision.com/cn/products/front-end-product/"]

        self.logger.info(f"HikvisionCrawler初始化完成，基础URL: {self.base_url}")

    def extract_product_details(self, url):
        """从产品页面提取产品详情"""
        try:
            self.driver.get(url)
            self.logger.info(f"正在加载产品页面: {url}")
            time.sleep(2)  # 等待页面加载

            # 获取产品名称和ID
            name_element = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".modelName > span")))
            name = name_element.text.strip()

            id_element = self.driver.find_element(By.CSS_SELECTOR, ".model > span")
            product_id = id_element.text.strip()

            self.logger.info(f"找到产品: {name} (ID: {product_id})")

            # 获取规格参数
            params = []
            spec_elements = self.driver.find_elements(By.CSS_SELECTOR, ".tech-specs-accordion-content-desc ul")
            self.logger.info(f"找到 {len(spec_elements)} 个规格参数区块")

            for ul in spec_elements:
                li_elements = ul.find_elements(By.TAG_NAME, "li")
                # 从第二个li元素开始，按照要求
                for li in li_elements[1:]:
                    try:
                        spans = li.find_elements(By.TAG_NAME, "span")
                        if len(spans) >= 2:
                            param_name = spans[0].text.strip()
                            param_value = spans[1].text.strip()
                            params.append({
                                "paramName": param_name,
                                "param": param_value
                            })
                    except Exception as e:
                        self.logger.warning(f"提取参数时出错 {url}: {str(e)}")

            # 准备产品数据
            product_data = {
                'product_id': product_id,
                'product_name': name,
                'params': params
            }

            self.logger.info(f"成功提取产品详情，共 {len(params)} 个参数")
            return product_data

        except Exception as e:
            self.logger.error(f"提取产品详情时出错 {url}: {str(e)}")
            return None

    def get_links_from_page(self, url, selector, mode=True):
        """重写获取页面链接的方法，处理onclick属性中的链接"""
        links = []
        try:
            if mode:
                self.driver.get(url)
                self.logger.info(f"正在加载页面: {url}")
                time.sleep(2)  # 等待页面加载

            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
            self.logger.info(f"找到 {len(elements)} 个潜在链接元素")

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

            self.logger.info(f"成功提取 {len(links)} 个链接")
            return links
        except Exception as e:
            self.logger.error(f"获取链接时出错 {url}: {str(e)}")
            return []

    def process_category_page(self, url):
        """处理类别页面，包括分页处理"""
        # 如果是主页，需要先获取所有类别链接，然后获取子类别链接
        if url == self.start_urls[0]:
            category_links = self.get_links_from_page(url, ".tile-card")
            self.logger.info(f"在主页上找到 {len(category_links)} 个类别链接")

            subcategory_links = []
            for link in category_links:
                sub_links = self.get_links_from_page(link, ".tile-card")
                subcategory_links.extend(sub_links)
                self.logger.info(f"从 {link} 找到 {len(sub_links)} 个子类别链接")

            self.logger.info(f"子类别链接总数: {len(subcategory_links)}")

            # 从所有子类别链接中获取产品链接
            all_product_links = []
            for sub_link in subcategory_links:
                product_links = self.process_product_page_with_pagination(sub_link)
                all_product_links.extend(product_links)

            return all_product_links
        else:
            # 如果直接提供了产品类别页面，直接处理
            return self.process_product_page_with_pagination(url)

    def process_product_page_with_pagination(self, url):
        """处理带分页的产品页面"""
        product_links = []

        # 处理第一页
        page_product_links = self.get_links_from_page(url, ".btn-details-link")
        product_links.extend(page_product_links)
        self.logger.info(f"第1页找到 {len(page_product_links)} 个产品链接")

        # 检查分页
        try:
            self.driver.get(url)
            pagination_elements = self.driver.find_elements(By.CSS_SELECTOR, ".paginationjs-pages > ul > li")
            self.logger.info(f"找到 {len(pagination_elements)} 个分页元素")

            # 如果有分页并且元素数量大于3（排除上一页、当前页和下一页）
            if len(pagination_elements) > 3:
                page_num = int(pagination_elements[-2].get_attribute("data-num"))
                self.logger.info(f"总共有 {page_num} 页需要处理")

                for page_idx in range(2, page_num + 1):
                    try:
                        # 找到并点击分页元素
                        pagination_elements = self.driver.find_elements(By.CSS_SELECTOR,
                                                                        ".paginationjs-pages > ul > li")
                        page_element = pagination_elements[-1]
                        self.logger.info(f"点击下一页按钮，处理第 {page_idx} 页")
                        page_element.click()
                        time.sleep(3)  # 点击后等待页面加载

                        # 获取新页面中的产品链接
                        page_product_links = self.get_links_from_page(self.driver.current_url, ".btn-details-link",
                                                                      False)
                        product_links.extend(page_product_links)
                        self.logger.info(f"第 {page_idx} 页找到 {len(page_product_links)} 个产品链接")

                    except Exception as e:
                        self.logger.error(f"处理分页 {page_idx} 时出错 {url}: {str(e)}")
            else:
                self.logger.info("没有找到分页元素或只有一页")

        except Exception as e:
            self.logger.error(f"检查分页时出错 {url}: {str(e)}")

        self.logger.info(f"该类别页面共找到 {len(product_links)} 个产品链接")
        return product_links
