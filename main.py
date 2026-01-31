#!/usr/bin/env python3
import argparse
import sys
from config import Config
from crawler import ImageCrawler
from logger_config import setup_logger


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='图片爬虫 - 从网站爬取并下载图片',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py
  python main.py --url https://example.com --depth 2 --max-pages 20
  python main.py --use-proxy --proxy-file proxies.txt
  python main.py --output my_images --workers 10
        """
    )
    
    parser.add_argument(
        '--url',
        type=str,
        default='https://8se.me/photos/sort-hot.html',
        help='列表页URL (默认: https://8se.me/photos/sort-hot.html)'
    )
    
    parser.add_argument(
        '--list-pages',
        type=int,
        default=Config.LIST_PAGES,
        help=f'要爬取的列表页数量 (默认: {Config.LIST_PAGES})'
    )
    
    parser.add_argument(
        '--depth',
        type=int,
        default=Config.DETAIL_DEPTH,
        help=f'套图详情页分页深度 (默认: {Config.DETAIL_DEPTH})'
    )
    
    parser.add_argument(
        '--max-pages',
        type=int,
        default=Config.MAX_PAGES,
        help=f'最大爬取页面数 (默认: {Config.MAX_PAGES})'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        default=Config.OUTPUT_DIR,
        help=f'输出目录 (默认: {Config.OUTPUT_DIR})'
    )
    
    parser.add_argument(
        '--workers',
        type=int,
        default=Config.MAX_WORKERS,
        help=f'下载线程数 (默认: {Config.MAX_WORKERS})'
    )
    
    parser.add_argument(
        '--use-proxy',
        action='store_true',
        default=Config.USE_PROXY,
        help='使用代理'
    )
    
    parser.add_argument(
        '--proxy-file',
        type=str,
        default=Config.PROXY_LIST_FILE,
        help=f'代理列表文件 (默认: {Config.PROXY_LIST_FILE})'
    )
    
    parser.add_argument(
        '--no-headless',
        action='store_true',
        help='显示浏览器窗口（非无头模式）'
    )

    parser.add_argument(
        '--cookie-file',
        type=str,
        default=Config.COOKIE_FILE,
        help=f'Cookie文件路径 (默认: {Config.COOKIE_FILE})'
    )
    
    parser.add_argument(
        '--min-delay',
        type=float,
        default=Config.MIN_DELAY,
        help=f'最小请求延迟（秒） (默认: {Config.MIN_DELAY})'
    )
    
    parser.add_argument(
        '--max-delay',
        type=float,
        default=Config.MAX_DELAY,
        help=f'最大请求延迟（秒） (默认: {Config.MAX_DELAY})'
    )
    
    parser.add_argument(
        '--no-skip-existing',
        action='store_true',
        help='不跳过已存在的文件'
    )
    
    return parser.parse_args()


def main():
    """主函数"""
    logger = setup_logger('main')
    
    try:
        args = parse_arguments()
        
        Config.START_URL = args.url
        Config.LIST_PAGES = args.list_pages
        Config.DETAIL_DEPTH = args.depth
        Config.MAX_PAGES = args.max_pages
        Config.OUTPUT_DIR = args.output
        Config.MAX_WORKERS = args.workers
        Config.USE_PROXY = args.use_proxy
        Config.PROXY_LIST_FILE = args.proxy_file
        Config.HEADLESS = not args.no_headless
        Config.COOKIE_FILE = args.cookie_file
        Config.MIN_DELAY = args.min_delay
        Config.MAX_DELAY = args.max_delay
        Config.SKIP_EXISTING = not args.no_skip_existing
        
        if Config.USE_PROXY:
            Config.load_proxies_from_file()
            if not Config.PROXY_LIST:
                logger.warning("启用了代理但代理列表为空，请检查 config.py 或代理文件")
        
        logger.info("图片爬虫启动")
        logger.info(f"配置: URL={Config.START_URL}, 列表页数={Config.LIST_PAGES}, "
                   f"套图深度={Config.DETAIL_DEPTH}, 使用代理={Config.USE_PROXY}")
        
        crawler = ImageCrawler(Config)
        
        crawler.crawl()
        
        logger.info("爬虫运行完成")
        
    except KeyboardInterrupt:
        logger.info("\n用户中断，退出程序")
        sys.exit(0)
    except Exception as e:
        logger.error(f"发生错误: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
