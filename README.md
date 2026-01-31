# 图片爬虫系统 (Image Crawler)

一个功能完整的Python图片爬虫系统，支持浏览器模拟、代理轮换、递归爬取等高级功能。

## 🔄 版本更新说明

**最新版本已从 Playwright 迁移到 Selenium！**

- ✅ **更好的 Windows 兼容性**: Selenium 在 Windows 环境下运行更稳定
- ✅ **自动驱动管理**: 使用 webdriver-manager 自动管理 ChromeDriver
- ✅ **更少的依赖**: 移除 playwright 依赖，降低安装复杂性
- ✅ **更好的性能**: 同步操作减少异步复杂性

## ✨ 功能特性

### 核心功能
- 🌐 **浏览器模拟**: 使用 Selenium WebDriver 模拟真实浏览器操作
- 🔄 **代理支持**: 完整的代理池管理和轮换机制
- 🔗 **递归爬取**: 支持多层级页面递归爬取
- 📥 **并发下载**: 多线程并发下载图片
- 📊 **进度显示**: 实时显示下载进度
- 📝 **日志记录**: 完善的日志系统
- 🤖 **反爬虫对策**: 随机延迟、请求头伪装、代理轮换

### 高级特性
- ✅ 图片格式验证（使用 Pillow）
- ✅ 断点续传（跳过已下载文件）
- ✅ URL去重机制
- ✅ robots.txt 支持
- ✅ 动态内容加载
- ✅ 详细的统计信息

## 📋 系统要求

- Python 3.8+
- 操作系统: Windows / Linux / macOS

## 🚀 快速开始

### 方式一：自动安装（推荐）

```bash
# 克隆或下载项目
cd image-crawler

# 运行自动安装脚本
./setup.sh

# 激活虚拟环境
source venv/bin/activate

# 运行爬虫
python main.py --help
```

### 方式二：手动安装

#### 1. 创建虚拟环境

```bash
# 克隆或下载项目
cd image-crawler

# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
# Linux/macOS:
source venv/bin/activate
# Windows:
# venv\Scripts\activate

# 安装 Python 依赖
pip install -r requirements.txt

# 安装 Chrome 浏览器（如果未安装）
# Windows: 下载并安装 Chrome
# Linux: sudo apt-get install google-chrome-stable
# macOS: brew install --cask google-chrome
```

#### 2. 基本使用

**注意：运行前请先激活虚拟环境**

```bash
# 激活虚拟环境（如果还未激活）
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# 直接运行（使用默认配置）
python main.py

# 指定起始URL
python main.py --url https://example.com

# 自定义爬取深度和页面数
python main.py --depth 2 --max-pages 20

# 使用更多下载线程
python main.py --workers 10
```

#### 3. 使用代理

**方式一：通过配置文件**

1. 复制示例文件：
```bash
cp proxies.txt.example proxies.txt
```

2. 编辑 `proxies.txt`，添加代理：
```
http://127.0.0.1:7890
http://proxy1.example.com:8080
http://user:pass@proxy2.example.com:3128
```

3. 运行爬虫：
```bash
python main.py --use-proxy
```

### 使用Cookie登录态（可选）

1. 准备包含Cookie的JSON文件（列表格式），例如:
```json
[
  {"name": "sessionid", "value": "your_value", "domain": "8se.me", "path": "/"}
]
```

2. 运行爬虫时指定Cookie文件：
```bash
python main.py --cookie-file cookies.json
```

**方式二：在 config.py 中配置**

编辑 `config.py` 文件，修改 `PROXY_LIST`：

```python
PROXY_LIST = [
    'http://127.0.0.1:7890',
    'http://proxy.example.com:8080',
]
```

然后运行：
```bash
python main.py --use-proxy
```

## ⚙️ 配置说明

### 命令行参数

```bash
python main.py [选项]

选项:
  --url URL              起始URL (默认: https://8se.me/)
  --depth N              最大爬取深度 (默认: 3)
  --max-pages N          最大爬取页面数 (默认: 50)
  --output DIR           输出目录 (默认: output)
  --workers N            下载线程数 (默认: 5)
  --use-proxy            使用代理
  --proxy-file FILE      代理列表文件 (默认: proxies.txt)
  --no-headless          显示浏览器窗口
  --cookie-file FILE     Cookie文件路径 (默认: cookies.json)
  --min-delay SECONDS    最小请求延迟 (默认: 1)
  --max-delay SECONDS    最大请求延迟 (默认: 3)
  --no-skip-existing     不跳过已存在的文件
  -h, --help             显示帮助信息
```

### 环境变量配置

复制 `.env.example` 为 `.env` 并修改：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
START_URL=https://8se.me/
MAX_DEPTH=3
MAX_PAGES=50
USE_PROXY=false
HEADLESS=true
COOKIE_FILE=cookies.json
```

### config.py 配置文件

主要配置项说明：

```python
START_URL = 'https://8se.me/'           # 起始URL
MAX_DEPTH = 3                            # 最大爬取深度
MAX_PAGES = 50                           # 最大页面数
OUTPUT_DIR = 'output'                    # 输出目录
MIN_DELAY = 1                            # 最小延迟（秒）
MAX_DELAY = 3                            # 最大延迟（秒）
MAX_WORKERS = 5                          # 下载线程数
USE_PROXY = False                        # 是否使用代理
HEADLESS = True                          # 无头模式
COOKIE_FILE = 'cookies.json'             # Cookie文件路径
RESPECT_ROBOTS_TXT = True                # 遵守robots.txt
MIN_IMAGE_SIZE = 10240                   # 最小图片大小（字节）
```

## 📁 项目结构

```
image-crawler/
├── main.py                 # 程序入口
├── crawler.py              # 爬虫核心类
├── config.py               # 配置文件
├── proxy_manager.py        # 代理管理器
├── logger_config.py        # 日志配置
├── requirements.txt        # Python依赖
├── .env.example            # 环境变量示例
├── proxies.txt.example     # 代理列表示例
├── README.md               # 说明文档
├── output/                 # 图片输出目录（自动创建）
│   ├── page1/
│   ├── page2/
│   └── ...
└── logs/                   # 日志目录（自动创建）
    └── crawler_*.log
```

## 📝 使用示例

### 示例 1: 基本爬取

```bash
python main.py --url https://example.com --depth 2 --max-pages 10
```

### 示例 2: 使用代理爬取

```bash
python main.py --use-proxy --proxy-file my_proxies.txt --depth 3
```

### 示例 3: 高性能爬取

```bash
python main.py --workers 20 --max-pages 100 --min-delay 0.5 --max-delay 1
```

### 示例 4: 调试模式（显示浏览器）

```bash
python main.py --no-headless --depth 1 --max-pages 5
```

## 🔧 代理配置详解

### 代理格式

支持以下格式：

```
# HTTP代理
http://IP:端口
http://用户名:密码@IP:端口

# HTTPS代理
https://IP:端口
https://用户名:密码@IP:端口

# SOCKS5代理（需要额外配置）
socks5://IP:端口
```

### 代理测试

爬虫会自动测试代理的可用性。你也可以手动测试：

```python
from proxy_manager import ProxyManager
from config import Config

Config.load_proxies_from_file()
proxy_manager = ProxyManager(Config.PROXY_LIST)
proxy_manager.test_all_proxies()
```

### 代理轮换策略

- 每次请求随机选择一个可用代理
- 失败的代理会被临时移除（5分钟后恢复）
- 自动重试机制

## 📊 输出说明

### 目录结构

```
output/
├── index/                  # 首页图片
│   ├── abc123.jpg
│   └── def456.png
├── gallery_photos/         # 相册页面图片
│   ├── img001.jpg
│   └── img002.jpg
└── ...
```

### 日志文件

```
logs/
└── crawler_20240130_120000.log
```

日志包含：
- 页面访问记录
- 图片下载状态
- 错误和警告信息
- 统计数据

## ⚠️ 注意事项

1. **合法使用**: 请遵守目标网站的服务条款和 robots.txt
2. **请求频率**: 建议设置合理的延迟，避免对服务器造成压力
3. **代理选择**: 使用可靠的代理服务，避免数据泄露
4. **存储空间**: 确保有足够的磁盘空间存储图片
5. **网络环境**: 某些网站可能需要特定的网络环境才能访问

## 🐛 常见问题

### Q1: 安装 Selenium 后运行失败

确保已安装 Chrome 浏览器：
```bash
# Windows: 下载并安装 Google Chrome
# Linux:
sudo apt-get install google-chrome-stable

# 验证 Chrome 是否正确安装
google-chrome --version
```

### Q2: ChromeDriver 自动下载失败

webdriver-manager 会自动下载 ChromeDriver，如果失败可以手动指定：

```python
# 在 crawler.py 中可以手动设置 ChromeDriver 路径
from selenium.webdriver.chrome.service import Service
service = Service('/path/to/chromedriver')
driver = webdriver.Chrome(service=service)
```

### Q3: 代理连接失败

- 检查代理格式是否正确
- 确认代理服务器正常运行
- 检查防火墙设置

### Q4: 图片下载失败

- 检查网络连接
- 尝试降低并发数（--workers）
- 增加请求延迟

### Q5: 内存占用过高

- 减少并发线程数（--workers）
- 减少最大页面数（--max-pages）
- 增加最小图片大小限制

## 🔒 安全建议

1. **不要上传代理列表到公共仓库**
2. **使用 .gitignore 排除敏感文件**
3. **定期更新依赖包**
4. **谨慎使用免费代理**

## 📈 性能优化

1. **调整并发数**: 根据网络和机器性能调整 `--workers`
2. **使用代理池**: 多个代理可以提高爬取速度
3. **调整延迟**: 在允许的范围内减少延迟
4. **启用断点续传**: 使用 `SKIP_EXISTING=true`

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

## 📮 联系方式

如有问题或建议，请提交 Issue。

---

**免责声明**: 本工具仅供学习和研究使用，使用者需自行承担法律责任。请遵守目标网站的服务条款和相关法律法规。
