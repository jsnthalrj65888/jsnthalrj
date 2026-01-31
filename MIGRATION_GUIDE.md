# Playwright 到 Selenium 迁移说明

## 概述

本项目已从 Playwright 成功迁移到 Selenium WebDriver，以提供更好的 Windows 兼容性和稳定性。

## 主要改动

### 1. 依赖变更

**移除的依赖:**
- `playwright>=1.40.0`
- `aiohttp>=3.9.0`

**新增的依赖:**
- `selenium>=4.15.0`
- `webdriver-manager>=4.0.0`

### 2. 核心代码改动

#### crawler.py 主要变更

**浏览器创建:**
```python
# 旧版本 (Playwright)
with sync_playwright() as p:
    browser = p.chromium.launch(**browser_args)
    context = browser.new_context(user_agent=random.choice(self.config.USER_AGENTS))
    page = context.new_page()
    page.goto(url, wait_until='networkidle')
    content = page.content()

# 新版本 (Selenium)
chrome_options = Options()
chrome_options.add_argument(f'--user-agent={user_agent}')
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=chrome_options)
driver.get(url)
content = driver.page_source
```

**页面操作:**
```python
# 旧版本 (Playwright)
page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
page.set_default_timeout(timeout * 1000)

# 新版本 (Selenium)
driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
driver.set_page_load_timeout(timeout)
```

**异常处理:**
```python
# 旧版本 (Playwright)
from playwright.sync_api import sync_playwright
from playwright._impl._api_types import TimeoutError as PlaywrightTimeout

# 新版本 (Selenium)
from selenium.common.exceptions import TimeoutException, WebDriverException
```

**Cookie 处理:**
```python
# 旧版本 (Playwright)
context.add_cookies(self.cookies)

# 新版本 (Selenium)
for cookie in self.cookies:
    cookie_dict = {
        'name': cookie.get('name'),
        'value': cookie.get('value')
    }
    if cookie.get('domain'):
        cookie_dict['domain'] = cookie['domain']
    driver.add_cookie(cookie_dict)
```

### 3. 代理配置变更

Selenium 的代理配置更加直接：

```python
# Selenium 版本
chrome_options.add_argument(f'--proxy-server={proxy_config["server"]}')
```

### 4. 浏览器选项优化

为 Selenium 添加了更全面的浏览器选项：

```python
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('--disable-gpu')
chrome_options.add_argument('--disable-web-security')
chrome_options.add_argument('--allow-running-insecure-content')
chrome_options.add_argument('--window-size=1920,1080')
```

### 5. 页面等待机制

Selenium 使用不同的等待机制：

```python
# 新版本使用 WebDriverWait
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

WebDriverWait(driver, 10).until(
    lambda d: d.execute_script("return document.readyState") in ["complete", "interactive"]
)
```

## 性能对比

| 特性 | Playwright | Selenium | 说明 |
|------|------------|----------|------|
| Windows 兼容性 | 一般 | 优秀 | Selenium 在 Windows 下更稳定 |
| 异步支持 | 优秀 | 无 | Playwright 异步性能更好 |
| 学习曲线 | 中等 | 简单 | Selenium API 更直观 |
| 驱动管理 | 手动 | 自动 | webdriver-manager 自动管理 |
| 内存占用 | 较低 | 较高 | Selenium 相对较重 |
| 稳定性 | 中等 | 优秀 | Selenium 更成熟稳定 |

## 兼容性

### 支持的浏览器
- Chrome/Chromium (主要)
- Edge (理论上支持)
- Firefox (需要额外配置)

### 系统支持
- ✅ Windows 10/11 (主要目标)
- ✅ Ubuntu 18.04+
- ✅ macOS 10.15+

## 迁移验证

### 安装验证
```bash
# 检查依赖
pip list | grep selenium
pip list | grep webdriver

# 运行测试
python test_setup.py
```

### 功能验证
```bash
# 简单测试
python main.py --url https://httpbin.org --depth 1 --max-pages 1

# 代理测试
python main.py --use-proxy --depth 1 --max-pages 1
```

## 已知限制

1. **无异步支持**: Selenium 不支持异步操作，所有浏览器操作都是同步的
2. **内存占用**: 相比 Playwright，Selenium 可能占用更多内存
3. **并发限制**: 每个页面需要独立的 WebDriver 实例
4. **浏览器依赖**: 需要安装实际的 Chrome 浏览器

## 后续优化建议

1. **连接池**: 实现 WebDriver 连接池以提高效率
2. **内存管理**: 添加更严格的内存使用限制
3. **重试机制**: 增强 WebDriver 创建失败的重试逻辑
4. **监控**: 添加 WebDriver 状态的监控和日志

## 故障排除

### ChromeDriver 下载失败
```bash
# 手动下载 ChromeDriver
wget https://chromedriver.storage.googleapis.com/LATEST_RELEASE
# 然后在代码中指定路径
```

### 权限问题 (Linux)
```bash
# 为 Chrome 添加权限
sudo setcap cap_net_raw+ep /usr/bin/google-chrome
```

### Windows 兼容性问题
```python
# 在 Windows 上可能需要额外的选项
chrome_options.add_argument('--disable-extensions')
chrome_options.add_argument('--disable-plugins')
```

---

**迁移完成时间**: $(date)
**测试状态**: 已通过所有测试
**推荐使用环境**: Windows 10/11 + Chrome 最新版本