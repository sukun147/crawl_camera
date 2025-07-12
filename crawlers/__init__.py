from .base_crawler import BaseCrawler
from .dahua_crawler import DahuaCrawler
from .hikvision_crawler import HikvisionCrawler
from .vivotek_crawler import VivotekCrawler
from .acti_crawler import ActiCrawler
from .everfocus_crawler import EverFocusCrawler
from .cpplusworld_crawler import CPlusWorldCrawler
from .hisharp_crawler import HisharpCrawler

# 将所有爬虫类添加到__all__列表中，方便from crawlers import *的使用
__all__ = [
    'BaseCrawler',
    'DahuaCrawler',
    'HikvisionCrawler',
    'VivotekCrawler',
    'ActiCrawler',
    'EverFocusCrawler',
    'CPlusWorldCrawler',
    'HisharpCrawler'
]