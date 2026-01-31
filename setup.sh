#!/bin/bash
# 自动化安装脚本 (Selenium版本)

echo "================================"
echo "图片爬虫系统 - 自动安装 (Selenium版本)"
echo "================================"

# 检查Python版本
echo -e "\n检查Python版本..."
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到 python3，请先安装 Python 3.8+"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "Python 版本: $PYTHON_VERSION"

# 创建虚拟环境
echo -e "\n创建虚拟环境..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✓ 虚拟环境已创建"
else
    echo "✓ 虚拟环境已存在"
fi

# 激活虚拟环境并安装依赖
echo -e "\n安装Python依赖..."
source venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo "✓ Python依赖已安装"

# 检查Chrome浏览器
echo -e "\n检查Chrome浏览器..."
if command -v google-chrome &> /dev/null; then
    CHROME_VERSION=$(google-chrome --version)
    echo "✓ $CHROME_VERSION"
    echo "✓ Chrome浏览器已安装"
elif command -v chromium-browser &> /dev/null; then
    CHROMIUM_VERSION=$(chromium-browser --version)
    echo "✓ $CHROMIUM_VERSION"
    echo "✓ Chromium浏览器已安装"
else
    echo "⚠ 警告: 未检测到Chrome/Chromium浏览器"
    echo "请安装Chrome浏览器:"
    echo "  Ubuntu/Debian: sudo apt-get install google-chrome-stable"
    echo "  CentOS/RHEL: sudo yum install google-chrome-stable"
    echo "  macOS: brew install --cask google-chrome"
    echo "  Windows: 下载并安装 https://www.google.com/chrome/"
fi

# 创建配置文件
echo -e "\n创建配置文件..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "✓ 已创建 .env 配置文件"
else
    echo "✓ .env 文件已存在"
fi

# 运行测试
echo -e "\n运行系统测试..."
python test_setup.py

echo -e "\n================================"
echo "安装完成！"
echo "================================"
echo -e "\n使用方法:"
echo "1. 激活虚拟环境:"
echo "   source venv/bin/activate"
echo ""
echo "2. 运行爬虫:"
echo "   python main.py --help"
echo "   python main.py --url https://example.com --depth 2"
echo ""
echo "3. 配置代理（可选）:"
echo "   cp proxies.txt.example proxies.txt"
echo "   # 编辑 proxies.txt 添加代理"
echo "   python main.py --use-proxy"
echo ""
echo "注意: Selenium版本会自动管理ChromeDriver，无需手动安装"
echo "================================"
