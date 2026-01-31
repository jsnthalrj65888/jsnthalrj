#!/usr/bin/env python3
"""
测试脚本 - 验证爬虫系统的基本功能 (Selenium版本)
"""
import os
import sys


def test_imports():
    """测试所有模块是否可以正常导入"""
    print("测试模块导入...")
    try:
        import config
        print("✓ config 模块导入成功")
        
        import logger_config
        print("✓ logger_config 模块导入成功")
        
        import proxy_manager
        print("✓ proxy_manager 模块导入成功")
        
        import crawler
        print("✓ crawler 模块导入成功")
        
        import main
        print("✓ main 模块导入成功")
        
        return True
    except Exception as e:
        print(f"✗ 模块导入失败: {e}")
        return False


def test_dependencies():
    """测试依赖包是否已安装"""
    print("\n测试依赖包...")
    dependencies = [
        'selenium',
        'webdriver_manager',
        'requests',
        'bs4',
        'PIL',
        'dotenv',
        'lxml',
        'tqdm'
    ]
    
    all_ok = True
    for dep in dependencies:
        try:
            __import__(dep)
            print(f"✓ {dep} 已安装")
        except ImportError:
            print(f"✗ {dep} 未安装")
            all_ok = False
    
    return all_ok


def test_selenium_webdriver():
    """测试Selenium WebDriver是否可以工作"""
    print("\n测试Selenium WebDriver...")
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        from webdriver_manager.chrome import ChromeDriverManager
        
        # 测试Chrome选项
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        # 测试webdriver-manager
        service = Service(ChromeDriverManager().install())
        
        print("✓ Selenium WebDriver 配置正常")
        print("✓ webdriver-manager 可用")
        
        return True
    except Exception as e:
        print(f"✗ Selenium WebDriver 测试失败: {e}")
        print("请确保已安装 Chrome 浏览器")
        return False


def test_config():
    """测试配置"""
    print("\n测试配置...")
    try:
        from config import Config
        
        print(f"✓ START_URL: {Config.START_URL}")
        print(f"✓ MAX_DEPTH: {Config.MAX_DEPTH}")
        print(f"✓ MAX_PAGES: {Config.MAX_PAGES}")
        print(f"✓ OUTPUT_DIR: {Config.OUTPUT_DIR}")
        print(f"✓ USE_PROXY: {Config.USE_PROXY}")
        
        return True
    except Exception as e:
        print(f"✗ 配置测试失败: {e}")
        return False


def test_logger():
    """测试日志系统"""
    print("\n测试日志系统...")
    try:
        from logger_config import setup_logger
        
        logger = setup_logger('test')
        logger.info("这是一条测试日志")
        
        if os.path.exists('logs'):
            print("✓ 日志目录已创建")
            log_files = os.listdir('logs')
            if log_files:
                print(f"✓ 日志文件已创建: {log_files[0]}")
            return True
        else:
            print("✗ 日志目录未创建")
            return False
    except Exception as e:
        print(f"✗ 日志测试失败: {e}")
        return False


def test_proxy_manager():
    """测试代理管理器"""
    print("\n测试代理管理器...")
    try:
        from proxy_manager import ProxyManager
        
        test_proxies = ['http://127.0.0.1:8080', 'http://127.0.0.1:8081']
        manager = ProxyManager(test_proxies)
        
        stats = manager.get_stats()
        print(f"✓ 代理管理器初始化成功")
        print(f"  总代理数: {stats['total']}")
        print(f"  可用代理数: {stats['available']}")
        
        return True
    except Exception as e:
        print(f"✗ 代理管理器测试失败: {e}")
        return False


def test_directories():
    """测试目录结构"""
    print("\n测试目录结构...")
    required_files = [
        'main.py',
        'crawler.py',
        'config.py',
        'proxy_manager.py',
        'logger_config.py',
        'requirements.txt',
        'README.md'
    ]
    
    all_ok = True
    for file in required_files:
        if os.path.exists(file):
            print(f"✓ {file} 存在")
        else:
            print(f"✗ {file} 不存在")
            all_ok = False
    
    return all_ok


def main():
    """运行所有测试"""
    print("=" * 60)
    print("图片爬虫系统 - 环境测试")
    print("=" * 60)
    
    tests = [
        ("目录结构", test_directories),
        ("模块导入", test_imports),
        ("依赖包", test_dependencies),
        ("Selenium WebDriver", test_selenium_webdriver),
        ("配置", test_config),
        ("日志系统", test_logger),
        ("代理管理器", test_proxy_manager),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"测试 {name} 时发生错误: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{name}: {status}")
    
    all_passed = all(result for _, result in results)
    
    print("=" * 60)
    if all_passed:
        print("✓ 所有测试通过！系统已准备就绪。")
        print("\n运行爬虫:")
        print("  python main.py --help")
        return 0
    else:
        print("✗ 部分测试失败，请检查上述错误。")
        print("\n安装依赖:")
        print("  pip install -r requirements.txt")
        print("\n确保安装Chrome浏览器:")
        print("  Ubuntu/Debian: sudo apt-get install google-chrome-stable")
        print("  Windows: 下载安装 https://www.google.com/chrome/")
        return 1


if __name__ == '__main__':
    sys.exit(main())
