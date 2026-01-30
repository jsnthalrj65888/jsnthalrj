# 快速开始指南

## 🚀 三步开始使用

### 步骤 1: 安装

```bash
# 运行自动安装脚本
./setup.sh
```

或者手动安装：

```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
playwright install chromium
```

### 步骤 2: 运行测试

```bash
# 激活虚拟环境（如果未激活）
source venv/bin/activate

# 运行系统测试
python test_setup.py
```

### 步骤 3: 开始爬取

```bash
# 基础使用 - 爬取默认网站（深度1，最多5页，适合测试）
python main.py --depth 1 --max-pages 5

# 自定义URL
python main.py --url https://example.com --depth 2 --max-pages 10

# 使用代理
python main.py --use-proxy --proxy-file proxies.txt
```

## 📝 常用命令示例

### 测试爬取（小规模）
```bash
# 只爬取首页，查看功能是否正常
python main.py --depth 0 --max-pages 1
```

### 中等规模爬取
```bash
# 爬取2层深度，最多20个页面
python main.py --depth 2 --max-pages 20 --workers 5
```

### 高性能爬取
```bash
# 使用更多线程，降低延迟
python main.py --depth 3 --max-pages 100 --workers 20 --min-delay 0.5 --max-delay 1
```

### 调试模式
```bash
# 显示浏览器窗口，便于调试
python main.py --no-headless --depth 1 --max-pages 5
```

### 使用代理
```bash
# 1. 创建代理文件
cp proxies.txt.example proxies.txt

# 2. 编辑 proxies.txt，添加你的代理
# http://127.0.0.1:7890
# http://user:pass@proxy.example.com:8080

# 3. 使用代理运行
python main.py --use-proxy
```

## 📊 查看结果

爬取完成后，图片将保存在 `output/` 目录中：

```bash
# 查看输出目录
ls -lh output/

# 查看日志
ls -lh logs/
tail -f logs/crawler_*.log
```

## ⚙️ 配置文件

### 使用环境变量

```bash
# 复制示例配置
cp .env.example .env

# 编辑配置
nano .env
```

### 常用配置项

```env
START_URL=https://8se.me/
MAX_DEPTH=3
MAX_PAGES=50
OUTPUT_DIR=output
USE_PROXY=false
HEADLESS=true
MIN_DELAY=1
MAX_DELAY=3
MAX_WORKERS=5
```

## 🔧 故障排除

### 问题1: 命令找不到

```bash
# 确保已激活虚拟环境
source venv/bin/activate

# 检查Python版本
python --version
```

### 问题2: Playwright浏览器未安装

```bash
# 重新安装浏览器
playwright install chromium
```

### 问题3: 代理连接失败

```bash
# 测试代理（修改为你的代理）
curl -x http://127.0.0.1:7890 https://www.google.com
```

### 问题4: 内存不足

```bash
# 减少并发数和页面数
python main.py --workers 3 --max-pages 10
```

## 📈 进阶使用

### 自定义User-Agent

编辑 `config.py`，修改 `USER_AGENTS` 列表。

### 调整图片过滤

编辑 `config.py`：

```python
MIN_IMAGE_SIZE = 10240  # 最小10KB
ALLOWED_IMAGE_FORMATS = ['jpg', 'jpeg', 'png', 'gif', 'webp']
```

### 自定义输出目录

```bash
python main.py --output my_images
```

### 跳过已下载文件

```bash
# 默认启用，如果要重新下载：
python main.py --no-skip-existing
```

## 🎯 最佳实践

1. **首次运行**: 使用小参数测试
   ```bash
   python main.py --depth 1 --max-pages 5
   ```

2. **检查日志**: 查看是否有错误
   ```bash
   tail -f logs/crawler_*.log
   ```

3. **逐步增加**: 确认正常后增加深度和页面数

4. **使用代理**: 对于大规模爬取，建议使用代理

5. **遵守规则**: 设置合理的延迟，尊重robots.txt

## 💡 提示

- 首次运行建议使用 `--depth 1 --max-pages 5` 测试
- 查看 `logs/` 目录了解爬取详情
- 图片保存在 `output/` 目录，按页面分组
- 使用 `Ctrl+C` 可以随时中断爬虫
- 中断后再次运行会跳过已下载的图片（如果启用了 `SKIP_EXISTING`）

## 📚 更多信息

查看完整文档：[README.md](README.md)
