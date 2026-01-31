import os
import time
import random
import hashlib
from urllib.parse import urljoin, urlparse
from typing import Set, List
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup
from PIL import Image
from io import BytesIO
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from urllib.robotparser import RobotFileParser
from tqdm import tqdm

from config import Config
from proxy_manager import ProxyManager
from logger_config import setup_logger


class ImageCrawler:
    """图片爬虫类 - Selenium版本"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = setup_logger('crawler')
        
        self.visited_urls: Set[str] = set()
        self.downloaded_images: Set[str] = set()
        
        self.proxy_manager = None
        if config.USE_PROXY and config.PROXY_LIST:
            self.proxy_manager = ProxyManager(config.PROXY_LIST, self.logger)
            self.logger.info(f"代理管理器已初始化，代理数量: {len(config.PROXY_LIST)}")
        
        self.robot_parser = None
        if config.RESPECT_ROBOTS_TXT:
            self._init_robots_parser()
        
        self.stats = {
            'pages_crawled': 0,
            'images_found': 0,
            'images_downloaded': 0,
            'images_failed': 0,
            'images_skipped': 0,
            'start_time': time.time()
        }

        self.cookies = self.config.load_cookies()
        if self.cookies:
            self.logger.info(f"已加载 {len(self.cookies)} 条Cookie")

        if not os.path.exists(config.OUTPUT_DIR):
            os.makedirs(config.OUTPUT_DIR)
            self.logger.info(f"创建输出目录: {config.OUTPUT_DIR}")
    
    def _init_robots_parser(self):
        """初始化robots.txt解析器"""
        try:
            self.robot_parser = RobotFileParser()
            robots_url = urljoin(self.config.START_URL, '/robots.txt')
            self.robot_parser.set_url(robots_url)
            self.robot_parser.read()
            self.logger.info(f"已加载 robots.txt: {robots_url}")
        except Exception as e:
            self.logger.warning(f"无法加载 robots.txt: {str(e)}")
            self.robot_parser = None
    
    def can_fetch(self, url: str) -> bool:
        """检查是否允许爬取该URL"""
        if not self.robot_parser:
            return True
        try:
            return self.robot_parser.can_fetch("*", url)
        except Exception as e:
            self.logger.warning(f"检查robots.txt时出错: {str(e)}")
            return True
    
    def _get_page_name(self, url: str) -> str:
        """从URL生成页面名称"""
        parsed = urlparse(url)
        path = parsed.path.strip('/').replace('/', '_')
        if not path:
            path = 'index'
        return path[:100]
    
    def _random_delay(self):
        """随机延迟"""
        delay = random.uniform(self.config.MIN_DELAY, self.config.MAX_DELAY)
        time.sleep(delay)
    
    def _is_valid_url(self, url: str, base_url: str) -> bool:
        """检查URL是否有效"""
        if not url:
            return False
        
        parsed = urlparse(url)
        base_parsed = urlparse(base_url)
        
        if parsed.scheme not in ['http', 'https']:
            return False
        
        if parsed.netloc != base_parsed.netloc:
            return False
        
        return True
    
    def _normalize_url(self, url: str) -> str:
        """标准化URL"""
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    
    def _create_driver(self, proxy_config=None):
        """创建WebDriver（Selenium版本替代Playwright浏览器）"""
        chrome_options = Options()
        
        # 基础选项
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-web-security')
        chrome_options.add_argument('--allow-running-insecure-content')
        
        # 设置User-Agent
        user_agent = random.choice(self.config.USER_AGENTS)
        chrome_options.add_argument(f'--user-agent={user_agent}')
        
        # 视窗大小设置
        chrome_options.add_argument('--window-size=1920,1080')
        
        # 代理设置
        if proxy_config:
            chrome_options.add_argument(f'--proxy-server={proxy_config["server"]}')
            self.logger.debug(f"使用代理: {proxy_config['server']}")
        
        # 无头模式设置
        if self.config.HEADLESS:
            chrome_options.add_argument('--headless')
        
        # 设置页面加载超时
        chrome_options.add_argument('--page-load-timeout=30')
        
        # 禁用图片加载以提高速度（可选）
        # chrome_options.add_argument('--disable-images')
        
        try:
            # 使用WebDriverManager自动管理ChromeDriver
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # 设置页面加载超时
            driver.set_page_load_timeout(self.config.TIMEOUT)
            
            # 设置脚本执行超时
            driver.set_script_timeout(self.config.TIMEOUT)
            
            # 设置隐式等待
            driver.implicitly_wait(10)
            
            return driver
            
        except Exception as e:
            self.logger.error(f"WebDriver创建失败: {str(e)}")
            raise
    
    def _load_cookies(self, driver):
        """加载Cookie到浏览器"""
        if not self.cookies:
            return
            
        try:
            for cookie in self.cookies:
                try:
                    # Selenium Cookie格式与Playwright不同，需要转换
                    cookie_dict = {
                        'name': cookie.get('name'),
                        'value': cookie.get('value')
                    }
                    
                    # 添加可选字段
                    if cookie.get('domain'):
                        cookie_dict['domain'] = cookie['domain']
                    if cookie.get('path'):
                        cookie_dict['path'] = cookie['path']
                    if cookie.get('secure') is not None:
                        cookie_dict['secure'] = cookie['secure']
                    if cookie.get('expiry'):
                        cookie_dict['expiry'] = cookie['expiry']
                    
                    driver.add_cookie(cookie_dict)
                except Exception as e:
                    self.logger.warning(f"添加Cookie失败: {str(e)}")
                    continue
                    
            self.logger.info(f"成功加载 {len(self.cookies)} 条Cookie")
            
        except Exception as e:
            self.logger.warning(f"加载Cookie时出错: {str(e)}")
    
    def _wait_for_page_load(self, driver, url):
        """等待页面加载完成"""
        try:
            # 等待页面标题变化，表示页面开始加载
            WebDriverWait(driver, 10).until(
                lambda d: d.execute_script("return document.readyState") in ["complete", "interactive"]
            )
            
            # 等待网络空闲（通过检查是否有未完成的请求）
            WebDriverWait(driver, 15).until(
                lambda d: d.execute_script("return performance.now()") > 0
            )
            
            # 执行滚动操作触发懒加载
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # 再次滚动确保触发所有懒加载
            driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
            
        except TimeoutException:
            self.logger.warning(f"页面加载超时: {url}")
        except Exception as e:
            self.logger.warning(f"页面加载等待异常: {str(e)}")
    
    def crawl_page(self, url: str, depth: int = 0) -> List[str]:
        """爬取单个页面，返回页面中的链接（Selenium版本）"""
        if depth > self.config.MAX_DEPTH:
            self.logger.debug(f"达到最大深度，跳过: {url}")
            return []

        if url in self.visited_urls:
            self.logger.debug(f"URL已访问过，跳过: {url}")
            return []

        if self.stats['pages_crawled'] >= self.config.MAX_PAGES:
            self.logger.info(f"达到最大页面数限制: {self.config.MAX_PAGES}")
            return []

        if not self.can_fetch(url):
            self.logger.warning(f"robots.txt禁止访问: {url}")
            return []

        self.visited_urls.add(url)
        self.logger.info(f"爬取页面 (深度 {depth}): {url}")

        driver = None
        proxy_config = None
        
        try:
            # 获取代理配置
            if self.proxy_manager:
                proxy_config = self.proxy_manager.get_proxy()
            
            # 创建WebDriver
            driver = self._create_driver(proxy_config)
            
            # 访问页面
            self.logger.debug(f"正在加载页面: {url}")
            driver.get(url)
            
            # 等待页面加载完成
            self._wait_for_page_load(driver, url)
            
            # 获取页面内容
            content = driver.page_source
            
            # 提取图片
            image_urls = self._extract_images_from_page(content, url)
            self.stats['images_found'] += len(image_urls)
            self.logger.info(f"在页面中找到 {len(image_urls)} 张图片")

            # 下载图片
            page_name = self._get_page_name(url)
            self._download_images(image_urls, page_name)

            # 提取链接
            links = self._extract_links_from_page(content, url)

            self.stats['pages_crawled'] += 1
            
            # 标记代理成功（如果使用了代理）
            if self.proxy_manager and proxy_config:
                self.proxy_manager.mark_proxy_success()
            
            return links

        except WebDriverException as e:
            self.logger.error(f"WebDriver错误 {url}: {str(e)}")
            if self.proxy_manager and proxy_config:
                self.proxy_manager.mark_proxy_failed()
            return []
        except Exception as e:
            self.logger.error(f"页面处理失败 {url}: {str(e)}")
            if self.proxy_manager and proxy_config:
                self.proxy_manager.mark_proxy_failed()
            return []
        finally:
            # 关闭浏览器
            if driver:
                try:
                    driver.quit()
                except Exception as e:
                    self.logger.warning(f"关闭WebDriver时出错: {str(e)}")
        
        # 添加随机延迟
        self._random_delay()
        return []
    
    def _extract_images_from_page(self, html: str, base_url: str) -> List[str]:
        """从页面中提取图片URL"""
        soup = BeautifulSoup(html, 'lxml')
        image_urls = set()
        
        for img in soup.find_all('img'):
            src = img.get('src') or img.get('data-src') or img.get('data-original')
            if src:
                full_url = urljoin(base_url, src)
                if self._is_image_url(full_url):
                    image_urls.add(full_url)
        
        for picture in soup.find_all('picture'):
            for source in picture.find_all('source'):
                srcset = source.get('srcset')
                if srcset:
                    urls = [s.strip().split()[0] for s in srcset.split(',')]
                    for url in urls:
                        full_url = urljoin(base_url, url)
                        if self._is_image_url(full_url):
                            image_urls.add(full_url)
        
        for link in soup.find_all('a'):
            href = link.get('href')
            if href and self._is_image_url(href):
                full_url = urljoin(base_url, href)
                image_urls.add(full_url)
        
        return list(image_urls)
    
    def _is_image_url(self, url: str) -> bool:
        """检查URL是否为图片"""
        parsed = urlparse(url)
        path = parsed.path.lower()
        return any(path.endswith(f'.{fmt}') for fmt in self.config.ALLOWED_IMAGE_FORMATS)
    
    def _extract_links_from_page(self, html: str, base_url: str) -> List[str]:
        """从页面中提取链接"""
        soup = BeautifulSoup(html, 'lxml')
        links = []
        
        for a in soup.find_all('a', href=True):
            href = a['href']
            full_url = urljoin(base_url, href)
            normalized_url = self._normalize_url(full_url)
            
            if self._is_valid_url(normalized_url, self.config.START_URL):
                if normalized_url not in self.visited_urls:
                    links.append(normalized_url)
        
        return links
    
    def _download_images(self, image_urls: List[str], page_name: str):
        """下载图片列表"""
        if not image_urls:
            return
        
        output_dir = os.path.join(self.config.OUTPUT_DIR, page_name)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        self.logger.info(f"开始下载 {len(image_urls)} 张图片到 {output_dir}")
        
        with ThreadPoolExecutor(max_workers=self.config.MAX_WORKERS) as executor:
            futures = {
                executor.submit(self._download_single_image, url, output_dir): url
                for url in image_urls
            }
            
            with tqdm(total=len(image_urls), desc=f"下载图片 [{page_name}]") as pbar:
                for future in as_completed(futures):
                    future.result()
                    pbar.update(1)
    
    def _download_single_image(self, url: str, output_dir: str) -> bool:
        """下载单张图片"""
        if url in self.downloaded_images:
            self.stats['images_skipped'] += 1
            return True
        
        url_hash = hashlib.md5(url.encode()).hexdigest()
        ext = os.path.splitext(urlparse(url).path)[1] or '.jpg'
        filename = f"{url_hash}{ext}"
        filepath = os.path.join(output_dir, filename)
        
        if self.config.SKIP_EXISTING and os.path.exists(filepath):
            self.logger.debug(f"文件已存在，跳过: {filename}")
            self.downloaded_images.add(url)
            self.stats['images_skipped'] += 1
            return True
        
        for attempt in range(self.config.MAX_RETRIES):
            try:
                headers = {
                    'User-Agent': random.choice(self.config.USER_AGENTS),
                    'Referer': self.config.START_URL
                }

                proxies = None
                if self.proxy_manager:
                    proxy = self.proxy_manager.get_proxy()
                    if proxy:
                        proxy_url = proxy['server']
                        proxies = {
                            'http': proxy_url,
                            'https': proxy_url
                        }

                cookie_jar = None
                if self.cookies:
                    cookie_jar = requests.cookies.RequestsCookieJar()
                    for cookie in self.cookies:
                        name = cookie.get('name')
                        value = cookie.get('value')
                        if not name or value is None:
                            continue
                        try:
                            cookie_jar.set_cookie(
                                requests.cookies.create_cookie(
                                    name=name,
                                    value=value,
                                    domain=cookie.get('domain'),
                                    path=cookie.get('path', '/'),
                                    secure=cookie.get('secure', False)
                                )
                            )
                        except Exception:
                            continue

                response = requests.get(
                    url,
                    headers=headers,
                    proxies=proxies,
                    timeout=self.config.TIMEOUT,
                    stream=True,
                    cookies=cookie_jar
                )
                response.raise_for_status()

                content = response.content
                
                if len(content) < self.config.MIN_IMAGE_SIZE:
                    self.logger.debug(f"图片太小，跳过: {url} ({len(content)} bytes)")
                    self.stats['images_skipped'] += 1
                    return False
                
                try:
                    img = Image.open(BytesIO(content))
                    img.verify()
                except Exception as e:
                    self.logger.warning(f"图片验证失败: {url} - {str(e)}")
                    self.stats['images_failed'] += 1
                    return False
                
                with open(filepath, 'wb') as f:
                    f.write(content)
                
                self.downloaded_images.add(url)
                self.stats['images_downloaded'] += 1
                self.logger.debug(f"下载成功: {filename} ({len(content)} bytes)")
                return True
                
            except Exception as e:
                self.logger.warning(f"下载失败 (尝试 {attempt + 1}/{self.config.MAX_RETRIES}): {url} - {str(e)}")
                if attempt == self.config.MAX_RETRIES - 1:
                    self.stats['images_failed'] += 1
                    if self.proxy_manager and proxies:
                        self.proxy_manager.mark_proxy_failed()
                time.sleep(1)
        
        return False
    
    def crawl(self):
        """开始爬取"""
        self.logger.info(f"=" * 60)
        self.logger.info(f"开始爬取 (Selenium版本): {self.config.START_URL}")
        self.logger.info(f"最大深度: {self.config.MAX_DEPTH}, 最大页面数: {self.config.MAX_PAGES}")
        self.logger.info(f"输出目录: {self.config.OUTPUT_DIR}")
        self.logger.info(f"使用代理: {self.config.USE_PROXY}")
        self.logger.info(f"=" * 60)
        
        queue = [(self.config.START_URL, 0)]
        
        while queue and self.stats['pages_crawled'] < self.config.MAX_PAGES:
            url, depth = queue.pop(0)
            
            links = self.crawl_page(url, depth)
            
            for link in links:
                if link not in self.visited_urls:
                    queue.append((link, depth + 1))
        
        self._print_stats()
    
    def _print_stats(self):
        """打印统计信息"""
        elapsed_time = time.time() - self.stats['start_time']
        
        self.logger.info(f"\n" + "=" * 60)
        self.logger.info(f"爬取完成！统计信息:")
        self.logger.info(f"=" * 60)
        self.logger.info(f"总耗时: {elapsed_time:.2f} 秒")
        self.logger.info(f"页面爬取数: {self.stats['pages_crawled']}")
        self.logger.info(f"图片发现数: {self.stats['images_found']}")
        self.logger.info(f"图片下载成功: {self.stats['images_downloaded']}")
        self.logger.info(f"图片下载失败: {self.stats['images_failed']}")
        self.logger.info(f"图片跳过: {self.stats['images_skipped']}")
        
        if self.stats['images_found'] > 0:
            success_rate = (self.stats['images_downloaded'] / self.stats['images_found']) * 100
            self.logger.info(f"下载成功率: {success_rate:.2f}%")
        
        if self.proxy_manager:
            proxy_stats = self.proxy_manager.get_stats()
            self.logger.info(f"代理统计: 总数={proxy_stats['total']}, "
                           f"可用={proxy_stats['available']}, "
                           f"失败={proxy_stats['failed']}")
        
        self.logger.info(f"=" * 60)