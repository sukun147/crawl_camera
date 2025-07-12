import argparse
import concurrent.futures
import logging
import os
import sys
from typing import List, Type, Optional

from crawlers import BaseCrawler


def ensure_dir_exists(directory):
    """确保目录存在，如果不存在则创建"""
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"创建目录: {directory}")


def setup_logging():
    """设置日志系统"""
    logger = logging.getLogger("main")
    logger.setLevel(logging.INFO)

    # 添加控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 添加文件处理器
    log_dir = "logs"
    ensure_dir_exists(log_dir)

    log_file_path = os.path.join(log_dir, "main.log")
    file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.info(f"日志将保存到: {log_file_path}")

    return logger


# 设置日志
logger = setup_logging()


def get_crawler_classes() -> List[Type[BaseCrawler]]:
    """
    使用__subclasses__()方法获取所有BaseCrawler的子类

    Returns:
        BaseCrawler子类列表
    """
    # 获取所有BaseCrawler的子类
    crawler_classes = BaseCrawler.__subclasses__()

    for cls in crawler_classes:
        logger.info(f"找到爬虫类: {cls.__name__}")

    return crawler_classes


def execute_crawler(crawler_class: Type[BaseCrawler], data_dir: str) -> str:
    """
    执行单个爬虫的函数，用于并行执行

    Args:
        crawler_class: 要执行的爬虫类
        data_dir: 数据保存目录

    Returns:
        执行结果信息
    """
    crawler_name = crawler_class.__name__
    try:
        logger.info(f"开始运行爬虫: {crawler_name}")
        crawler = crawler_class(data_dir=data_dir)
        crawler.run()
        logger.info(f"爬虫 {crawler_name} 运行完成")
        return f"爬虫 {crawler_name} 运行成功"
    except Exception as e:
        error_msg = f"运行爬虫 {crawler_name} 时出错: {str(e)}"
        logger.error(error_msg)
        return error_msg


def run_crawlers_parallel(crawler_classes: List[Type[BaseCrawler]],
                          data_dir: str = "data",
                          class_names: Optional[List[str]] = None,
                          max_workers: int = None) -> None:
    """
    并行运行指定的爬虫类

    Args:
        crawler_classes: 要运行的爬虫类列表
        data_dir: 数据保存目录
        class_names: 要运行的爬虫类名列表，如果为None则运行所有类
        max_workers: 最大工作线程数，None表示使用默认值(CPU数量*5)
    """
    if not crawler_classes:
        logger.error("未找到任何爬虫类")
        return

    # 如果指定了类名，只运行这些类
    if class_names:
        filtered_classes = []
        for cls in crawler_classes:
            if cls.__name__ in class_names:
                filtered_classes.append(cls)
                logger.info(f"将运行爬虫类: {cls.__name__}")

        if not filtered_classes:
            logger.error(f"未找到指定的爬虫类: {class_names}")
            return

        crawler_classes = filtered_classes

    # 并行执行所有爬虫
    logger.info(f"将并行执行 {len(crawler_classes)} 个爬虫任务")

    # 使用ThreadPoolExecutor并行执行爬虫
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 创建任务
        future_to_crawler = {
            executor.submit(execute_crawler, crawler_class, data_dir): crawler_class.__name__
            for crawler_class in crawler_classes
        }

        # 处理完成的任务
        for future in concurrent.futures.as_completed(future_to_crawler):
            crawler_name = future_to_crawler[future]
            try:
                result = future.result()
                logger.info(f"任务结果: {result}")
            except Exception as e:
                logger.error(f"爬虫 {crawler_name} 执行过程中发生异常: {str(e)}")

    logger.info("所有爬虫任务已完成")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="并行运行BaseCrawler的子类爬虫")
    parser.add_argument("--data-dir", type=str, default="data",
                        help="数据保存目录")
    parser.add_argument("--crawlers", type=str, nargs="*",
                        help="要运行的爬虫类名列表，如不指定则运行所有爬虫")
    parser.add_argument("--workers", type=int, default=None,
                        help="最大并行工作线程数，默认为CPU核心数*5")

    args = parser.parse_args()

    # 确保数据目录存在
    ensure_dir_exists(args.data_dir)

    logger.info("开始查找爬虫类...")
    crawler_classes = get_crawler_classes()

    if crawler_classes:
        logger.info(f"共找到 {len(crawler_classes)} 个爬虫类")
        run_crawlers_parallel(crawler_classes, args.data_dir, args.crawlers, args.workers)
    else:
        logger.error("未找到任何爬虫类，请确保爬虫文件已正确导入")


if __name__ == "__main__":
    main()
