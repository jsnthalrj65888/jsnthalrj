import os
import time
import random
import hashlib
import re
import base64
import json
from datetime import datetime
from urllib.parse import urljoin, urlparse
from typing import Set, List, Dict, Optional
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
            'photos_found': 0,
            'images_found': 0,
            'images_downloaded': 0,
            'images_failed': 0,
            'images_skipped': 0,
            'start_time': time.time()
        }
        
        # 套图追踪列表
        self.photo_sets: List[Dict] = []
        
        # 失败的下载记录
        self.failed_downloads: Dict[str, List[Dict]] = {}

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
    
    def _create_driver(self, proxy_config=None, download_dir=None):
        """创建WebDriver（Selenium版本替代Playwright浏览器）"""
        chrome_options = Options()
        
        # 设置偏好
        prefs = {
            'profile.managed_default_content_settings.images': 2,  # 禁用图片加载
            'profile.default_content_setting_values.notifications': 2,
        }
        if download_dir:
            prefs['download.default_directory'] = os.path.abspath(download_dir)
            
        chrome_options.add_experimental_option('prefs', prefs)

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
    
    def _extract_image_url_from_style(self, style: str) -> str:
        """从 style 属性中提取 background-image URL"""
        match = re.search(r'url\(["\']?(.*?)["\']?\)', style)
        if match:
            return match.group(1)
        return None

    def _generate_list_page_urls(self, list_pages: int) -> List[str]:
        """根据列表页数量生成所有列表页URL"""
        urls = []
        for page in range(1, list_pages + 1):
            if page == 1:
                url = self.config.START_URL
            else:
                if '?' in self.config.START_URL:
                    url = f"{self.config.START_URL}&page={page}"
                else:
                    url = f"{self.config.START_URL}?page={page}"
            urls.append(url)
        return urls

    def _get_image_filename(self, url: str, photo_id: str) -> str:
        """生成图片文件名"""
        url_hash = hashlib.md5(url.encode()).hexdigest()
        ext = os.path.splitext(urlparse(url).path)[1] or '.jpg'
        return f"{url_hash}{ext}"
    
    def _load_photo_metadata(self, photo_folder: str) -> Optional[Dict]:
        """读取套图元数据（用于恢复下载）"""
        metadata_path = os.path.join(photo_folder, 'metadata.json')
        if not os.path.exists(metadata_path):
            return None
        
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            self.logger.info(f"加载已存在的元数据: {photo_folder}")
            return metadata
        except Exception as e:
            self.logger.warning(f"加载元数据失败 {metadata_path}: {e}")
            return None
    
    def _save_photo_metadata(self, photo_folder: str, metadata: Dict):
        """保存套图元数据"""
        metadata_path = os.path.join(photo_folder, 'metadata.json')
        try:
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            self.logger.debug(f"保存元数据: {metadata_path}")
        except Exception as e:
            self.logger.error(f"保存元数据失败 {metadata_path}: {e}")
    
    def _update_photo_metadata(self, photo_folder: str, photo_id: str, photo_url: str, 
                              title: str = None, total_pages: int = None):
        """更新套图元数据"""
        metadata = self._load_photo_metadata(photo_folder) or {}
        
        # 初始化或更新基本信息
        if not metadata:
            metadata = {
                'title': title or f'套图 {photo_id}',
                'photo_id': photo_id,
                'photo_url': photo_url,
                'total_pages': total_pages or 0,
                'total_images': 0,
                'download_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'images_downloaded': 0,
                'images_failed': 0,
                'image_files': [],
                'failed_images': []
            }
        else:
            # 更新时间戳
            metadata['last_update'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            if title:
                metadata['title'] = title
            if total_pages:
                metadata['total_pages'] = total_pages
        
        # 统计当前文件夹中的图片
        image_files = []
        if os.path.exists(photo_folder):
            for filename in os.listdir(photo_folder):
                if filename.lower().endswith(tuple(f'.{fmt}' for fmt in self.config.ALLOWED_IMAGE_FORMATS)):
                    image_files.append(filename)
        
        metadata['image_files'] = sorted(image_files)
        metadata['images_downloaded'] = len(image_files)
        
        # 更新失败记录
        if photo_id in self.failed_downloads:
            metadata['failed_images'] = self.failed_downloads[photo_id]
            metadata['images_failed'] = len(self.failed_downloads[photo_id])
        
        # 保存元数据
        self._save_photo_metadata(photo_folder, metadata)
        
        return metadata
    
    def _generate_download_summary(self):
        """生成下载摘要报告"""
        elapsed_time = time.time() - self.stats['start_time']
        
        # 计算平均值
        avg_images = 0
        if len(self.photo_sets) > 0:
            total_images = sum(p.get('images_count', 0) for p in self.photo_sets)
            avg_images = total_images / len(self.photo_sets)
        
        # 统计成功和失败的套图
        photo_sets_downloaded = sum(1 for p in self.photo_sets if p.get('status') == 'success')
        photo_sets_failed = sum(1 for p in self.photo_sets if p.get('status') == 'failed')
        
        summary = {
            'run_date': datetime.fromtimestamp(self.stats['start_time']).strftime('%Y-%m-%d %H:%M:%S'),
            'total_duration_seconds': int(elapsed_time),
            'list_pages_crawled': self.config.LIST_PAGES,
            'photo_sets_found': self.stats['photos_found'],
            'photo_sets_downloaded': photo_sets_downloaded,
            'photo_sets_failed': photo_sets_failed,
            'total_images_downloaded': self.stats['images_downloaded'],
            'total_images_failed': self.stats['images_failed'],
            'total_images_skipped': self.stats['images_skipped'],
            'average_images_per_set': round(avg_images, 2),
            'photos': self.photo_sets
        }
        
        summary_path = os.path.join(self.config.OUTPUT_DIR, 'download_summary.json')
        try:
            with open(summary_path, 'w', encoding='utf-8') as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)
            self.logger.info(f"下载摘要已保存: {summary_path}")
            
            # 同时生成一个美化的文本版本
            self._generate_summary_text(summary, elapsed_time)
            
            return summary_path
        except Exception as e:
            self.logger.error(f"保存下载摘要失败: {e}")
            return None
    
    def _generate_summary_text(self, summary: Dict, elapsed_time: float):
        """生成美化的文本摘要"""
        summary_text_path = os.path.join(self.config.OUTPUT_DIR, 'download_summary.txt')
        try:
            with open(summary_text_path, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write("                        下载摘要报告\n")
                f.write("=" * 80 + "\n\n")
                
                f.write(f"运行时间: {summary['run_date']}\n")
                f.write(f"总耗时: {elapsed_time:.2f} 秒 ({int(elapsed_time // 60)} 分 {int(elapsed_time % 60)} 秒)\n\n")
                
                f.write("-" * 80 + "\n")
                f.write("统计信息\n")
                f.write("-" * 80 + "\n")
                f.write(f"列表页爬取数: {summary['list_pages_crawled']}\n")
                f.write(f"套图发现数: {summary['photo_sets_found']}\n")
                f.write(f"套图下载成功: {summary['photo_sets_downloaded']}\n")
                f.write(f"套图下载失败: {summary['photo_sets_failed']}\n")
                f.write(f"图片下载成功: {summary['total_images_downloaded']}\n")
                f.write(f"图片下载失败: {summary['total_images_failed']}\n")
                f.write(f"图片跳过: {summary['total_images_skipped']}\n")
                f.write(f"平均每套图片数: {summary['average_images_per_set']:.2f}\n\n")
                
                if summary['photo_sets_found'] > 0:
                    success_rate = (summary['photo_sets_downloaded'] / summary['photo_sets_found']) * 100
                    f.write(f"套图下载成功率: {success_rate:.2f}%\n")
                
                if summary['total_images_downloaded'] + summary['total_images_failed'] > 0:
                    img_success_rate = (summary['total_images_downloaded'] / 
                                       (summary['total_images_downloaded'] + summary['total_images_failed'])) * 100
                    f.write(f"图片下载成功率: {img_success_rate:.2f}%\n")
                
                f.write("\n" + "-" * 80 + "\n")
                f.write("套图详情\n")
                f.write("-" * 80 + "\n\n")
                
                for idx, photo in enumerate(summary['photos'], 1):
                    status_symbol = "✓" if photo['status'] == 'success' else "✗"
                    f.write(f"{idx}. [{status_symbol}] {photo['title']}\n")
                    f.write(f"   ID: {photo['photo_id']}\n")
                    f.write(f"   图片数: {photo['images_count']}\n")
                    if photo.get('images_failed', 0) > 0:
                        f.write(f"   失败数: {photo['images_failed']}\n")
                    f.write("\n")
                
                f.write("=" * 80 + "\n")
            
            self.logger.info(f"文本摘要已保存: {summary_text_path}")
        except Exception as e:
            self.logger.error(f"保存文本摘要失败: {e}")

    def _download_image_via_selenium(self, driver, img_url, photo_id, output_dir):
        """
        使用 Selenium 浏览器打开图片URL 进行下载
        这样可以完全绕过 CDN 的反爬虫检查
        """
        max_retries = 3
        filename = self._get_image_filename(img_url, photo_id)
        filepath = os.path.join(output_dir, filename)
        
        if os.path.exists(filepath) and self.config.SKIP_EXISTING:
            self.logger.debug(f"文件已存在，跳过: {filename}")
            self.downloaded_images.add(img_url)
            self.stats['images_skipped'] += 1
            return True
        
        for attempt in range(1, max_retries + 1):
            try:
                self.logger.debug(f"尝试下载 (Selenium, 尝试 {attempt}/{max_retries}): {img_url}")
                
                # 在新标签页中打开图片URL
                driver.execute_script(f"window.open('{img_url}', '_blank');")
                
                # 切换到新标签页
                driver.switch_to.window(driver.window_handles[-1])
                
                # 等待加载，虽然禁用了图片，但文档加载还是需要的
                # 我们可以等待 document.readyState
                try:
                    WebDriverWait(driver, 10).until(
                        lambda d: d.execute_script("return document.readyState") == "complete"
                    )
                except:
                    pass
                
                # 使用 JavaScript 触发 XHR 下载并返回 base64
                # 这种方法即使在禁用图片显示的情况下也工作，只要网络请求能成功
                script = """
                var url = arguments[0];
                var callback = arguments[1];
                var xhr = new XMLHttpRequest();
                xhr.open('GET', url, true);
                xhr.responseType = 'blob';
                xhr.onload = function() {
                    var reader = new FileReader();
                    reader.readAsDataURL(xhr.response);
                    reader.onloadend = function() {
                        callback(reader.result);
                    }
                };
                xhr.onerror = function() {
                    callback(null);
                };
                xhr.send();
                """
                
                base64_data = driver.execute_async_script(script, img_url)
                
                if base64_data:
                    # 移除 data:image/xxx;base64, 前缀
                    if ',' in base64_data:
                        base64_data = base64_data.split(',')[1]
                    
                    image_data = base64.b64decode(base64_data)
                    
                    if len(image_data) < self.config.MIN_IMAGE_SIZE:
                        self.logger.warning(f"下载的图片太小: {len(image_data)} bytes")
                    else:
                        with open(filepath, 'wb') as f:
                            f.write(image_data)
                        
                        self.logger.info(f"下载成功: {filename} ({len(image_data)} bytes)")
                        self.downloaded_images.add(img_url)
                        self.stats['images_downloaded'] += 1
                        
                        # 关闭新标签页
                        driver.close()
                        driver.switch_to.window(driver.window_handles[0])
                        return True
                
                # 如果 JS 方法失败，关闭标签页重试
                driver.close()
                driver.switch_to.window(driver.window_handles[0])
                time.sleep(1)
                
            except Exception as e:
                self.logger.warning(f"下载失败 (尝试 {attempt}/{max_retries}): {str(e)[:100]}")
                
                # 关闭额外标签页并返回主标签页
                try:
                    while len(driver.window_handles) > 1:
                        driver.switch_to.window(driver.window_handles[-1])
                        driver.close()
                    driver.switch_to.window(driver.window_handles[0])
                except:
                    pass
                
                if attempt < max_retries:
                    time.sleep(2)
        
        self.stats['images_failed'] += 1
        self.logger.error(f"最终下载失败，已放弃: {img_url}")
        return False

    def _crawl_photo_detail(self, photo_url: str, max_pages: int):
        """爬取单个套图的详情页（可能有多个分页）"""
        photo_start_time = time.time()
        photo_title = None
        photo_id = None
        
        try:
            # 提取 photo_id
            # 示例: https://8se.me/photo/id-697cc68a53ac0.html -> 697cc68a53ac0
            # 或者: https://8se.me/photo/id-697cc68a53ac0/1.html -> 697cc68a53ac0
            photo_id = photo_url.split('id-')[-1].split('.')[0].split('/')[0] if '/id-' in photo_url else None
            
            if not photo_id:
                self.logger.warning(f"无法从URL提取photo_id: {photo_url}")
                return
            
            # 准备输出目录
            output_dir = os.path.join(self.config.OUTPUT_DIR, photo_id)
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            # 检查是否已有元数据（支持断点续传）
            existing_metadata = self._load_photo_metadata(output_dir)
            if existing_metadata:
                self.logger.info(f"发现已存在的下载，继续下载: {photo_id}")
                photo_title = existing_metadata.get('title')
            
            # 使用同一个driver处理所有分页，减少启动开销
            driver = None
            proxy_config = None
            
            try:
                if self.proxy_manager:
                    proxy_config = self.proxy_manager.get_proxy()
                
                # 创建带有下载目录配置的Driver
                driver = self._create_driver(proxy_config, download_dir=output_dir)

                for page in range(1, max_pages + 1):
                    page_url = f"https://8se.me/photo/id-{photo_id}/{page}.html"
                    self.logger.info(f"  爬取套图分页: {page}/{max_pages} -> {page_url}")
                    
                    try:
                        driver.get(page_url)
                        time.sleep(self.config.MIN_DELAY) # 使用配置的延迟
                        
                        soup = BeautifulSoup(driver.page_source, 'html.parser')
                        
                        # 第一页时提取标题
                        if page == 1 and not photo_title:
                            title_elem = soup.find('h1')
                            if not title_elem:
                                title_elem = soup.find('title')
                            if title_elem:
                                photo_title = title_elem.get_text(strip=True)
                                self.logger.info(f"  套图标题: {photo_title}")
                        
                        # 提取该分页的所有图片
                        photo_images = soup.find_all('div', class_='item photo-image')
                        
                        self.logger.info(f"  发现 {len(photo_images)} 张图片")
                        
                        for img_item in photo_images:
                            # 提取图片信息
                            img_div = img_item.find('div', class_='img')
                            
                            if img_div and img_div.get('style'):
                                # 从 background-image 提取URL
                                img_url = self._extract_image_url_from_style(img_div['style'])
                                if img_url:
                                    if not img_url.startswith('http'):
                                        img_url = urljoin(page_url, img_url)
                                    
                                    self.stats['images_found'] += 1
                                    
                                    # 使用 Selenium 直接下载
                                    self._download_image_via_selenium(driver, img_url, photo_id, output_dir)
                                    
                                    # 图片间稍微延迟，避免太快
                                    time.sleep(0.5)
                        
                        self.stats['pages_crawled'] += 1
                        
                        # 检查是否还有下一页
                        pager = soup.find('div', class_='pager')
                        if pager:
                            next_link = pager.find('a', class_='next')
                            if not next_link or 'disabled' in next_link.get('class', []):
                                self.logger.info(f"  套图 {photo_id} 已到最后一页")
                                break
                        else:
                            # 如果没发现分页器，可能就一页
                            break
                        
                        # 随机延迟，避免请求过于频繁
                        time.sleep(0.5 + random.uniform(0, 1))
                        
                    except Exception as e:
                        self.logger.warning(f"爬取分页失败 {page_url}: {e}")
                        break
                        
                if self.proxy_manager and proxy_config:
                    self.proxy_manager.mark_proxy_success()
                
                # 更新元数据
                metadata = self._update_photo_metadata(
                    output_dir, 
                    photo_id, 
                    photo_url, 
                    title=photo_title, 
                    total_pages=max_pages
                )
                
                # 添加到套图列表
                photo_duration = time.time() - photo_start_time
                photo_info = {
                    'title': photo_title or f'套图 {photo_id}',
                    'photo_id': photo_id,
                    'photo_url': photo_url,
                    'status': 'success',
                    'images_count': metadata['images_downloaded'],
                    'images_failed': metadata.get('images_failed', 0),
                    'total_pages': max_pages,
                    'duration_seconds': int(photo_duration)
                }
                self.photo_sets.append(photo_info)
                self.logger.info(f"套图 {photo_id} 下载完成，成功 {metadata['images_downloaded']} 张，失败 {metadata.get('images_failed', 0)} 张")
                    
            except Exception as e:
                self.logger.error(f"处理套图详情页出错 {photo_url}: {e}")
                if self.proxy_manager and proxy_config:
                    self.proxy_manager.mark_proxy_failed()
                
                # 标记为失败的套图
                if photo_id:
                    metadata = self._update_photo_metadata(
                        output_dir, 
                        photo_id, 
                        photo_url, 
                        title=photo_title, 
                        total_pages=max_pages
                    )
                    photo_info = {
                        'title': photo_title or f'套图 {photo_id}',
                        'photo_id': photo_id,
                        'photo_url': photo_url,
                        'status': 'failed',
                        'images_count': metadata.get('images_downloaded', 0),
                        'images_failed': metadata.get('images_failed', 0),
                        'error': str(e),
                        'duration_seconds': int(time.time() - photo_start_time)
                    }
                    self.photo_sets.append(photo_info)
            finally:
                if driver:
                    driver.quit()
        
        except Exception as e:
            self.logger.error(f"处理套图详情页逻辑出错 {photo_url}: {e}")
            # 记录失败的套图
            if photo_id:
                photo_info = {
                    'title': photo_title or f'套图 {photo_id}',
                    'photo_id': photo_id,
                    'photo_url': photo_url,
                    'status': 'failed',
                    'images_count': 0,
                    'error': str(e),
                    'duration_seconds': int(time.time() - photo_start_time)
                }
                self.photo_sets.append(photo_info)

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
            self._download_images_simple(image_urls, page_name)

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
    
    def _download_images(self, image_urls: List[str], photo_id: str, show_urls: List[str] = None):
        """下载图片列表"""
        if not image_urls:
            return
        
        output_dir = os.path.join(self.config.OUTPUT_DIR, photo_id)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        self.logger.info(f"开始下载 {len(image_urls)} 张图片到 {output_dir}")
        
        with ThreadPoolExecutor(max_workers=self.config.MAX_WORKERS) as executor:
            futures = []
            
            for idx, url in enumerate(image_urls):
                show_url = show_urls[idx] if show_urls and idx < len(show_urls) else None
                future = executor.submit(self._download_single_image, url, output_dir, photo_id, show_url)
                futures.append(future)
            
            with tqdm(total=len(image_urls), desc=f"下载图片 [{photo_id}]") as pbar:
                for future in futures:
                    try:
                        future.result()
                    except Exception as e:
                        self.logger.warning(f"图片下载任务失败: {e}")
                    pbar.update(1)
    
    def _download_images_simple(self, image_urls: List[str], page_name: str):
        """下载图片列表（简单版本，用于一般页面）"""
        if not image_urls:
            return
        
        output_dir = os.path.join(self.config.OUTPUT_DIR, page_name)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        self.logger.info(f"开始下载 {len(image_urls)} 张图片到 {output_dir}")
        
        with ThreadPoolExecutor(max_workers=self.config.MAX_WORKERS) as executor:
            futures = {
                executor.submit(self._download_single_image, url, output_dir, None, None): url
                for url in image_urls
            }
            
            with tqdm(total=len(image_urls), desc=f"下载图片 [{page_name}]") as pbar:
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        self.logger.warning(f"图片下载任务失败: {e}")
                    pbar.update(1)

    def _get_browser_headers(self, referer_url: str = None) -> dict:
        """生成完整的浏览器请求头"""
        headers = {
            'User-Agent': random.choice(self.config.USER_AGENTS),
            'Accept': 'image/avif,image/webp,image/apng,image/*,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Sec-Fetch-Dest': 'image',
            'Sec-Fetch-Mode': 'no-cors',
            'Sec-Fetch-Site': 'cross-site',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
        }
        
        # 设置Referer头
        if referer_url:
            headers['Referer'] = referer_url
        else:
            headers['Referer'] = self.config.START_URL
            
        return headers

    def _get_hq_image_url(self, thumb_url: str) -> List[str]:
        """将缩略图URL转换为高清版本URL列表"""
        urls_to_try = [thumb_url]
        
        # 提取基础信息
        if '_600x0' in thumb_url:
            base_url = thumb_url.replace('_600x0', '')
            # 尝试不同分辨率
            hq_urls = [
                thumb_url.replace('_600x0', '_2000x0'),
                thumb_url.replace('_600x0', '_1200x0'),
                thumb_url.replace('_600x0', '_800x0'),
                base_url + '.webp',
                base_url + '.jpg',
                base_url + '.jpeg',
                base_url + '.png',
            ]
            urls_to_try.extend(hq_urls)
        
        return urls_to_try

    def _get_image_from_photo_show_page(self, driver, photo_id: str) -> List[str]:
        """访问photoShow页面获取高清图片链接"""
        image_urls = []
        
        try:
            # 构造photoShow页面URL
            show_urls = [
                f"https://8se.me/photoShow.html?id={photo_id}",
                f"https://8se.me/photo/show/id-{photo_id}.html"
            ]
            
            for show_url in show_urls:
                try:
                    self.logger.debug(f"访问photoShow页面: {show_url}")
                    driver.get(show_url)
                    time.sleep(2)
                    
                    soup = BeautifulSoup(driver.page_source, 'html.parser')
                    
                    # 查找图片标签
                    img_tags = soup.find_all('img')
                    for img in img_tags:
                        src = img.get('src') or img.get('data-src') or img.get('data-original')
                        if src and self._is_image_url(src):
                            if not src.startswith('http'):
                                src = urljoin(show_url, src)
                            if src not in image_urls:
                                image_urls.append(src)
                    
                    # 查找背景图片
                    for div in soup.find_all('div', style=True):
                        style = div.get('style', '')
                        if 'background-image' in style:
                            bg_url = self._extract_image_url_from_style(style)
                            if bg_url:
                                if not bg_url.startswith('http'):
                                    bg_url = urljoin(show_url, bg_url)
                                if bg_url not in image_urls:
                                    image_urls.append(bg_url)
                    
                    if image_urls:
                        self.logger.debug(f"从photoShow页面获取到 {len(image_urls)} 个图片链接")
                        break
                        
                except Exception as e:
                    self.logger.debug(f"photoShow页面访问失败 {show_url}: {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"获取photoShow页面图片失败: {e}")
        
        return image_urls

    def _get_current_cookies(self, driver=None) -> dict:
        """获取当前浏览器会话的有效Cookie"""
        try:
            if driver:
                # 获取Selenium的Cookie
                selenium_cookies = driver.get_cookies()
                cookie_dict = {}
                for cookie in selenium_cookies:
                    cookie_dict[cookie['name']] = cookie['value']
                return cookie_dict
            else:
                # 返回配置文件中的Cookie
                if self.cookies:
                    cookie_dict = {}
                    for cookie in self.cookies:
                        name = cookie.get('name')
                        value = cookie.get('value')
                        if name and value:
                            cookie_dict[name] = value
                    return cookie_dict
        except Exception as e:
            self.logger.warning(f"获取Cookie失败: {e}")
        return {}

    def _download_single_image(self, url: str, output_dir: str, photo_id: str = None, show_url: str = None, driver=None) -> bool:
        """下载单张图片（增强版，支持反爬虫对策）"""
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
        
        # 重试配置
        max_retries = 5
        retry_delays = [2, 3, 5, 8, 10]  # 递增延迟
        
        # 获取完整的URL列表（缩略图 + 高清版本）
        urls_to_try = self._get_hq_image_url(url)
        
        for attempt in range(1, max_retries + 1):
            try:
                # 如果是403错误且有photo_id，尝试从photoShow页面获取
                if attempt == 3 and photo_id:
                    driver = None
                    try:
                        self.logger.info(f"403错误，尝试通过photoShow页面获取高清图片: {photo_id}")
                        driver = self._create_driver()
                        show_image_urls = self._get_image_from_photo_show_page(driver, photo_id)
                        if show_image_urls:
                            # 将photoShow页面的URL添加到尝试列表前面
                            urls_to_try = show_image_urls + urls_to_try
                    finally:
                        if driver:
                            driver.quit()
                
                # 尝试不同的URL
                current_url = None
                for try_url in urls_to_try:
                    self.logger.debug(f"尝试下载: {try_url}")
                    
                    headers = self._get_browser_headers(show_url or self.config.START_URL)
                    
                    proxies = None
                    if self.proxy_manager:
                        proxy = self.proxy_manager.get_proxy()
                        if proxy:
                            proxy_url = proxy['server']
                            proxies = {
                                'http': proxy_url,
                                'https': proxy_url
                            }

                    # 使用当前有效的Cookie
                    cookies = self._get_current_cookies(driver)

                    response = requests.get(
                        try_url,
                        headers=headers,
                        proxies=proxies,
                        timeout=15,  # 增加超时时间
                        stream=True,
                        cookies=cookies,
                        allow_redirects=True
                    )

                    # 检查响应状态
                    if response.status_code == 200:
                        # 验证是否为有效的图片
                        content_type = response.headers.get('content-type', '').lower()
                        if 'image' in content_type:
                            content = response.content
                            
                            if len(content) < self.config.MIN_IMAGE_SIZE:
                                self.logger.debug(f"图片太小，跳过: {try_url} ({len(content)} bytes)")
                                continue  # 尝试下一个URL
                            
                            try:
                                img = Image.open(BytesIO(content))
                                img.verify()
                            except Exception as e:
                                self.logger.warning(f"图片验证失败: {try_url} - {str(e)}")
                                continue  # 尝试下一个URL
                            
                            # 保存图片
                            with open(filepath, 'wb') as f:
                                f.write(content)
                            
                            self.downloaded_images.add(url)
                            self.stats['images_downloaded'] += 1
                            self.logger.info(f"下载成功: {filename} ({len(content)} bytes) from {try_url}")
                            return True
                        else:
                            self.logger.debug(f"响应不是图片: {content_type} from {try_url}")
                            continue
                    
                    elif response.status_code == 403:
                        self.logger.warning(f"403 Forbidden: {try_url}")
                        if attempt == max_retries - 1:
                            break  # 最后一次尝试，不再尝试其他URL
                        continue  # 尝试下一个URL
                    
                    elif response.status_code == 429:
                        self.logger.warning(f"429 Too Many Requests: {try_url}")
                        break  # 暂停所有重试
                    
                    elif response.status_code >= 500:
                        self.logger.warning(f"服务器错误 {response.status_code}: {try_url}")
                        continue  # 尝试下一个URL
                    
                    else:
                        self.logger.debug(f"HTTP {response.status_code}: {try_url}")
                        continue  # 尝试下一个URL
                
                # 如果尝试了所有URL都失败，进行延迟重试
                if attempt < max_retries:
                    delay = retry_delays[attempt - 1]
                    self.logger.info(f"等待 {delay} 秒后重试... (尝试 {attempt}/{max_retries})")
                    time.sleep(delay)
                
            except requests.exceptions.Timeout:
                self.logger.warning(f"下载超时 (尝试 {attempt}/{max_retries}): {url}")
                if attempt < max_retries:
                    time.sleep(retry_delays[attempt - 1])
            
            except requests.exceptions.ConnectionError:
                self.logger.warning(f"连接错误 (尝试 {attempt}/{max_retries}): {url}")
                if attempt < max_retries:
                    time.sleep(retry_delays[attempt - 1])
            
            except Exception as e:
                self.logger.error(f"下载出错 (尝试 {attempt}/{max_retries}): {url} - {str(e)}")
                if attempt < max_retries:
                    time.sleep(retry_delays[attempt - 1])
        
        # 所有重试都失败了
        self.stats['images_failed'] += 1
        self.logger.error(f"最终下载失败，已放弃: {url}")
        
        # 记录失败的下载
        if photo_id:
            if photo_id not in self.failed_downloads:
                self.failed_downloads[photo_id] = []
            self.failed_downloads[photo_id].append({
                'url': url,
                'filename': filename,
                'reason': '下载失败（所有重试均失败）',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
        
        return False
    
    def crawl(self):
        """
        主爬取方法，根据 list_pages 参数爬取多个列表页
        """
        try:
            self.logger.info(f"=" * 60)
            self.logger.info(f"开始爬取 (8se.me 优化版): {self.config.START_URL}")
            self.logger.info(f"列表页数: {self.config.LIST_PAGES}, 套图深度: {self.config.DETAIL_DEPTH}")
            self.logger.info(f"输出目录: {self.config.OUTPUT_DIR}")
            self.logger.info(f"使用代理: {self.config.USE_PROXY}")
            self.logger.info(f"=" * 60)

            # 获取所有列表页URL
            list_urls = self._generate_list_page_urls(self.config.LIST_PAGES)
            self.logger.info(f"将爬取 {len(list_urls)} 页列表页")
            
            all_photo_urls = []
            
            # 1. 爬取所有列表页，收集套图详情页URL
            driver = None
            proxy_config = None
            try:
                if self.proxy_manager:
                    proxy_config = self.proxy_manager.get_proxy()
                driver = self._create_driver(proxy_config)

                for idx, list_url in enumerate(list_urls, 1):
                    self.logger.info(f"爬取列表页 {idx}/{len(list_urls)}: {list_url}")
                    
                    try:
                        driver.get(list_url)
                        time.sleep(self.config.MIN_DELAY)
                        
                        # 解析页面，提取套图链接
                        soup = BeautifulSoup(driver.page_source, 'html.parser')
                        photo_items = soup.find_all('div', class_='item photo')
                        
                        page_count = len(photo_items)
                        self.logger.info(f"列表页 {idx} 发现 {page_count} 个套图")
                        
                        # 提取每个套图的详情页URL
                        for item in photo_items:
                            link = item.find('a')
                            if link and 'href' in link.attrs:
                                photo_url = link['href']
                                if not photo_url.startswith('http'):
                                    photo_url = urljoin(self.config.START_URL, photo_url)
                                
                                if photo_url not in all_photo_urls:
                                    all_photo_urls.append(photo_url)
                                    # self.logger.debug(f"发现套图: {photo_url}")
                        
                        self.stats['pages_crawled'] += 1
                    except Exception as e:
                        self.logger.error(f"处理列表页失败 {list_url}: {e}")
                
                if self.proxy_manager and proxy_config:
                    self.proxy_manager.mark_proxy_success()
            finally:
                if driver:
                    driver.quit()
            
            self.logger.info(f"总共发现 {len(all_photo_urls)} 个套图")
            self.stats['photos_found'] = len(all_photo_urls)
            
            # 2. 对每个套图进行深度爬取（分页）
            for photo_idx, photo_url in enumerate(all_photo_urls, 1):
                self.logger.info(f"正在处理套图 {photo_idx}/{len(all_photo_urls)}: {photo_url}")
                
                # 调用详情页爬取方法
                self._crawl_photo_detail(photo_url, self.config.DETAIL_DEPTH)
                
                # 请求延迟
                time.sleep(self.config.MIN_DELAY)
            
            self.logger.info(f"爬取完成！共处理 {len(all_photo_urls)} 个套图")
            
        except Exception as e:
            self.logger.error(f"爬虫执行出错: {e}")
        finally:
            self._print_stats()
            # 生成下载摘要
            summary_path = self._generate_download_summary()
            if summary_path:
                self.logger.info(f"\n{'='*60}")
                self.logger.info(f"下载摘要已生成: {summary_path}")
                self.logger.info(f"{'='*60}\n")
    
    def _print_stats(self):
        """打印统计信息"""
        elapsed_time = time.time() - self.stats['start_time']
        
        self.logger.info(f"\n" + "=" * 60)
        self.logger.info(f"爬取完成！统计信息:")
        self.logger.info(f"=" * 60)
        self.logger.info(f"总耗时: {elapsed_time:.2f} 秒 ({int(elapsed_time // 60)} 分 {int(elapsed_time % 60)} 秒)")
        self.logger.info(f"列表页爬取数: {self.config.LIST_PAGES}")
        self.logger.info(f"总页面爬取数: {self.stats['pages_crawled']}")
        self.logger.info(f"套图发现数: {self.stats['photos_found']}")
        
        # 套图统计
        photo_sets_downloaded = sum(1 for p in self.photo_sets if p.get('status') == 'success')
        photo_sets_failed = sum(1 for p in self.photo_sets if p.get('status') == 'failed')
        self.logger.info(f"套图下载成功: {photo_sets_downloaded}")
        self.logger.info(f"套图下载失败: {photo_sets_failed}")
        
        self.logger.info(f"图片发现数: {self.stats['images_found']}")
        self.logger.info(f"图片下载成功: {self.stats['images_downloaded']}")
        self.logger.info(f"图片下载失败: {self.stats['images_failed']}")
        self.logger.info(f"图片跳过: {self.stats['images_skipped']}")
        
        if self.stats['photos_found'] > 0:
            photo_success_rate = (photo_sets_downloaded / self.stats['photos_found']) * 100
            self.logger.info(f"套图下载成功率: {photo_success_rate:.2f}%")
        
        if self.stats['images_found'] > 0:
            success_rate = (self.stats['images_downloaded'] / self.stats['images_found']) * 100
            self.logger.info(f"图片下载成功率: {success_rate:.2f}%")
        
        if self.proxy_manager:
            proxy_stats = self.proxy_manager.get_stats()
            self.logger.info(f"代理统计: 总数={proxy_stats['total']}, "
                           f"可用={proxy_stats['available']}, "
                           f"失败={proxy_stats['failed']}")
        
        self.logger.info(f"=" * 60)