# 元数据和下载统计功能

## 功能概述

本爬虫系统现在支持完整的元数据管理和下载统计功能，方便用户查询、管理和恢复下载。

## 主要特性

### 1. 套图元数据 (metadata.json)

每个套图文件夹中会自动创建 `metadata.json` 文件，包含以下信息：

```json
{
  "title": "套图标题",
  "photo_id": "697cc68a53ac0",
  "photo_url": "https://8se.me/photo/id-697cc68a53ac0.html",
  "total_pages": 10,
  "total_images": 0,
  "download_date": "2024-01-31 12:34:56",
  "last_update": "2024-01-31 12:35:30",
  "images_downloaded": 145,
  "images_failed": 5,
  "image_files": [
    "abc123def.jpg",
    "def456ghi.jpg",
    ...
  ],
  "failed_images": [
    {
      "url": "https://example.com/image.jpg",
      "filename": "xyz789.jpg",
      "reason": "下载失败（所有重试均失败）",
      "timestamp": "2024-01-31 12:35:20"
    }
  ]
}
```

#### 字段说明

- `title`: 套图标题（从页面提取）
- `photo_id`: 套图唯一标识符
- `photo_url`: 套图详情页URL
- `total_pages`: 套图总分页数
- `total_images`: 预计图片总数（可选）
- `download_date`: 首次下载时间
- `last_update`: 最后更新时间
- `images_downloaded`: 成功下载的图片数量
- `images_failed`: 下载失败的图片数量
- `image_files`: 已下载的图片文件名列表（按字母排序）
- `failed_images`: 失败的下载记录列表

### 2. 下载摘要报告 (download_summary.json)

爬虫运行完成后，会在输出目录根目录生成 `download_summary.json`：

```json
{
  "run_date": "2024-01-31 12:00:00",
  "total_duration_seconds": 3600,
  "list_pages_crawled": 5,
  "photo_sets_found": 50,
  "photo_sets_downloaded": 48,
  "photo_sets_failed": 2,
  "total_images_downloaded": 5000,
  "total_images_failed": 120,
  "total_images_skipped": 300,
  "average_images_per_set": 104.17,
  "photos": [
    {
      "title": "套图标题1",
      "photo_id": "abc123",
      "photo_url": "https://8se.me/photo/id-abc123.html",
      "status": "success",
      "images_count": 150,
      "images_failed": 5,
      "total_pages": 10,
      "duration_seconds": 120
    },
    {
      "title": "套图标题2",
      "photo_id": "def456",
      "photo_url": "https://8se.me/photo/id-def456.html",
      "status": "failed",
      "images_count": 0,
      "error": "下载失败原因",
      "duration_seconds": 30
    }
  ]
}
```

#### 字段说明

- `run_date`: 爬虫运行开始时间
- `total_duration_seconds`: 总耗时（秒）
- `list_pages_crawled`: 爬取的列表页数量
- `photo_sets_found`: 发现的套图总数
- `photo_sets_downloaded`: 成功下载的套图数量
- `photo_sets_failed`: 失败的套图数量
- `total_images_downloaded`: 图片下载成功总数
- `total_images_failed`: 图片下载失败总数
- `total_images_skipped`: 跳过的图片总数（已存在）
- `average_images_per_set`: 平均每套图片数
- `photos`: 所有套图的详细信息列表

### 3. 文本摘要报告 (download_summary.txt)

同时生成易读的文本格式摘要：

```
================================================================================
                        下载摘要报告
================================================================================

运行时间: 2024-01-31 12:00:00
总耗时: 3600.00 秒 (60 分 0 秒)

--------------------------------------------------------------------------------
统计信息
--------------------------------------------------------------------------------
列表页爬取数: 5
套图发现数: 50
套图下载成功: 48
套图下载失败: 2
图片下载成功: 5000
图片下载失败: 120
图片跳过: 300
平均每套图片数: 104.17

套图下载成功率: 96.00%
图片下载成功率: 97.66%

--------------------------------------------------------------------------------
套图详情
--------------------------------------------------------------------------------

1. [✓] 套图标题1
   ID: abc123
   图片数: 150

2. [✗] 套图标题2
   ID: def456
   图片数: 0
   失败数: 5

================================================================================
```

## 断点续传功能

### 工作原理

1. 开始爬取套图前，系统会检查是否存在 `metadata.json`
2. 如果存在，会读取已下载的文件列表
3. 下载时会自动跳过已存在的文件
4. 更新元数据中的统计信息

### 使用方法

只需重新运行爬虫，系统会自动识别并继续未完成的下载：

```bash
python main.py --url https://8se.me/ --list-pages 5 --detail-depth 10
```

如果之前的下载中断，再次运行相同命令即可继续。

## 文件结构示例

```
output/
├── download_summary.json       # 下载摘要（JSON格式）
├── download_summary.txt        # 下载摘要（文本格式）
├── abc123/                     # 套图1文件夹
│   ├── metadata.json          # 套图1的元数据
│   ├── 1a2b3c4d.jpg          # 图片文件
│   ├── 5e6f7g8h.jpg
│   └── ...
├── def456/                     # 套图2文件夹
│   ├── metadata.json          # 套图2的元数据
│   ├── 9i0j1k2l.jpg
│   └── ...
└── ...
```

## API 说明

### ImageCrawler 新增方法

#### `_load_photo_metadata(photo_folder: str) -> Optional[Dict]`

读取套图元数据（用于恢复下载）。

**参数：**
- `photo_folder`: 套图文件夹路径

**返回：**
- 元数据字典，如果不存在返回 None

#### `_save_photo_metadata(photo_folder: str, metadata: Dict)`

保存套图元数据。

**参数：**
- `photo_folder`: 套图文件夹路径
- `metadata`: 元数据字典

#### `_update_photo_metadata(photo_folder: str, photo_id: str, photo_url: str, title: str = None, total_pages: int = None) -> Dict`

更新套图元数据（自动统计文件夹中的图片）。

**参数：**
- `photo_folder`: 套图文件夹路径
- `photo_id`: 套图ID
- `photo_url`: 套图URL
- `title`: 套图标题（可选）
- `total_pages`: 总分页数（可选）

**返回：**
- 更新后的元数据字典

#### `_generate_download_summary() -> str`

生成下载摘要报告。

**返回：**
- 摘要文件路径

## 日志输出示例

```
2024-01-31 12:34:56 - INFO - 加载已存在的元数据: output/abc123
2024-01-31 12:34:56 - INFO - 发现已存在的下载，继续下载: abc123
2024-01-31 12:35:00 - INFO - 套图 abc123 下载完成，成功 145 张，失败 5 张
2024-01-31 12:40:00 - INFO - 下载摘要已保存: output/download_summary.json
2024-01-31 12:40:00 - INFO - 文本摘要已保存: output/download_summary.txt
```

## 数据分析

使用 Python 可以轻松分析下载数据：

```python
import json

# 读取摘要
with open('output/download_summary.json', 'r', encoding='utf-8') as f:
    summary = json.load(f)

# 分析
print(f"总成功率: {summary['photo_sets_downloaded'] / summary['photo_sets_found'] * 100:.2f}%")
print(f"平均每套图片: {summary['average_images_per_set']:.2f}")

# 找出失败的套图
failed_photos = [p for p in summary['photos'] if p['status'] == 'failed']
for photo in failed_photos:
    print(f"失败: {photo['title']} - {photo.get('error', 'Unknown')}")

# 找出图片最多的套图
top_photos = sorted(summary['photos'], key=lambda p: p.get('images_count', 0), reverse=True)[:10]
for i, photo in enumerate(top_photos, 1):
    print(f"{i}. {photo['title']}: {photo['images_count']} 张图片")
```

## 注意事项

1. **磁盘空间**: 元数据文件很小（通常<10KB），不会占用太多空间
2. **并发安全**: 当前实现不支持多进程同时写入同一套图
3. **版本兼容**: 元数据格式可能在未来版本中扩展，但保持向后兼容
4. **编码**: 所有JSON文件使用UTF-8编码，支持中文

## 故障排除

### 元数据文件损坏

如果元数据文件损坏，删除它即可：

```bash
rm output/abc123/metadata.json
```

重新运行爬虫会创建新的元数据。

### 摘要文件生成失败

检查输出目录权限：

```bash
chmod 755 output/
```

### 统计数字不准确

元数据基于文件系统扫描，如果手动修改了文件，统计可能不准确。建议重新生成元数据。

## 未来改进

- [ ] 支持导出为CSV格式
- [ ] 提供Web界面查看统计
- [ ] 支持自定义元数据字段
- [ ] 添加图片质量分析
- [ ] 支持多语言标题提取
