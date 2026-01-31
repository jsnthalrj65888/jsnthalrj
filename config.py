import os
import json
from dotenv import load_dotenv

load_dotenv()


class Config:
    """爬虫配置类"""
    
    START_URL = os.getenv('START_URL', 'https://8se.me/')
    
    MAX_DEPTH = int(os.getenv('MAX_DEPTH', '3'))
    
    MAX_PAGES = int(os.getenv('MAX_PAGES', '50'))
    
    OUTPUT_DIR = os.getenv('OUTPUT_DIR', 'output')
    
    LOGS_DIR = os.getenv('LOGS_DIR', 'logs')
    
    MIN_DELAY = float(os.getenv('MIN_DELAY', '1'))
    MAX_DELAY = float(os.getenv('MAX_DELAY', '3'))
    
    MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
    
    TIMEOUT = int(os.getenv('TIMEOUT', '30'))
    
    MAX_WORKERS = int(os.getenv('MAX_WORKERS', '5'))
    
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    ]

    COOKIE_FILE = os.getenv('COOKIE_FILE', 'cookies.json')

    PROXY_LIST = [
        # 格式: 'http://proxy_ip:port' 或 'http://username:password@proxy_ip:port'
        # 示例:
        # 'http://127.0.0.1:7890',
        # 'http://user:pass@proxy.example.com:8080',
    ]

    PROXY_LIST_FILE = os.getenv('PROXY_LIST_FILE', 'proxies.txt')

    USE_PROXY = os.getenv('USE_PROXY', 'false').lower() == 'true'

    HEADLESS = os.getenv('HEADLESS', 'true').lower() == 'true'

    RESPECT_ROBOTS_TXT = os.getenv('RESPECT_ROBOTS_TXT', 'true').lower() == 'true'

    MIN_IMAGE_SIZE = int(os.getenv('MIN_IMAGE_SIZE', '10240'))

    ALLOWED_IMAGE_FORMATS = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp']

    SKIP_EXISTING = os.getenv('SKIP_EXISTING', 'true').lower() == 'true'

    @classmethod
    def load_proxies_from_file(cls):
        """从文件加载代理列表"""
        if os.path.exists(cls.PROXY_LIST_FILE):
            with open(cls.PROXY_LIST_FILE, 'r', encoding='utf-8') as f:
                proxies = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                cls.PROXY_LIST.extend(proxies)

    @classmethod
    def load_cookies(cls) -> list:
        """从文件加载Cookies"""
        if not os.path.exists(cls.COOKIE_FILE):
            return []

        try:
            with open(cls.COOKIE_FILE, 'r', encoding='utf-8') as file:
                data = json.load(file)
            if isinstance(data, list):
                return data
            return []
        except (json.JSONDecodeError, OSError):
            return []
