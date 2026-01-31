import random
import time
from typing import Optional, List
import requests
from logger_config import setup_logger


class ProxyManager:
    """代理管理器"""
    
    def __init__(self, proxy_list: List[str], logger=None):
        self.proxy_list = proxy_list.copy() if proxy_list else []
        self.available_proxies = self.proxy_list.copy()
        self.failed_proxies = {}
        self.logger = logger or setup_logger('proxy_manager')
        self.current_proxy = None
        
        if not self.proxy_list:
            self.logger.warning("代理列表为空，将不使用代理")
    
    def get_proxy(self) -> Optional[dict]:
        """获取一个可用的代理"""
        if not self.proxy_list:
            return None
        
        self._clean_failed_proxies()
        
        if not self.available_proxies:
            self.logger.warning("所有代理都不可用，重置代理列表")
            self.available_proxies = self.proxy_list.copy()
            self.failed_proxies.clear()
        
        proxy_url = random.choice(self.available_proxies)
        self.current_proxy = proxy_url
        
        proxy_dict = {
            'server': proxy_url
        }
        
        return proxy_dict
    
    def mark_proxy_failed(self, proxy_url: Optional[str] = None):
        """标记代理失败"""
        if proxy_url is None:
            proxy_url = self.current_proxy
        
        if proxy_url and proxy_url in self.available_proxies:
            self.available_proxies.remove(proxy_url)
            self.failed_proxies[proxy_url] = time.time()
            self.logger.warning(f"代理标记为失败: {proxy_url}")
    
    def _clean_failed_proxies(self, timeout=300):
        """清理超时的失败代理，使其可以重新使用"""
        current_time = time.time()
        expired_proxies = [
            proxy for proxy, fail_time in self.failed_proxies.items()
            if current_time - fail_time > timeout
        ]
        
        for proxy in expired_proxies:
            del self.failed_proxies[proxy]
            if proxy not in self.available_proxies:
                self.available_proxies.append(proxy)
                self.logger.info(f"代理恢复可用: {proxy}")
    
    def test_proxy(self, proxy_url: str, test_url: str = 'https://www.google.com', timeout: int = 10) -> bool:
        """测试代理是否可用"""
        try:
            proxies = {
                'http': proxy_url,
                'https': proxy_url
            }
            response = requests.get(test_url, proxies=proxies, timeout=timeout)
            if response.status_code == 200:
                self.logger.info(f"代理可用: {proxy_url}")
                return True
            else:
                self.logger.warning(f"代理返回状态码 {response.status_code}: {proxy_url}")
                return False
        except Exception as e:
            self.logger.error(f"代理测试失败 {proxy_url}: {str(e)}")
            return False
    
    def test_all_proxies(self, test_url: str = 'https://www.google.com'):
        """测试所有代理"""
        if not self.proxy_list:
            self.logger.info("没有代理需要测试")
            return
        
        self.logger.info(f"开始测试 {len(self.proxy_list)} 个代理...")
        working_proxies = []
        
        for proxy in self.proxy_list:
            if self.test_proxy(proxy, test_url):
                working_proxies.append(proxy)
        
        self.available_proxies = working_proxies
        self.logger.info(f"测试完成，可用代理数: {len(working_proxies)}/{len(self.proxy_list)}")
    
    def get_stats(self) -> dict:
        """获取代理统计信息"""
        return {
            'total': len(self.proxy_list),
            'available': len(self.available_proxies),
            'failed': len(self.failed_proxies)
        }
