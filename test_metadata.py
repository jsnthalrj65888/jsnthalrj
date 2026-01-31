#!/usr/bin/env python3
"""
测试元数据功能
"""

import os
import json
import shutil
import tempfile
from datetime import datetime

from config import Config
from crawler import ImageCrawler


def test_metadata_creation():
    """测试元数据创建功能"""
    print("=" * 60)
    print("测试 1: 元数据创建")
    print("=" * 60)
    
    # 创建临时目录
    with tempfile.TemporaryDirectory() as temp_dir:
        config = Config()
        config.OUTPUT_DIR = temp_dir
        crawler = ImageCrawler(config)
        
        # 创建测试套图目录
        photo_id = "test_photo_123"
        photo_folder = os.path.join(temp_dir, photo_id)
        os.makedirs(photo_folder)
        
        # 创建一些测试图片文件
        for i in range(5):
            test_file = os.path.join(photo_folder, f"test_image_{i}.jpg")
            with open(test_file, 'w') as f:
                f.write("test image content")
        
        # 更新元数据
        metadata = crawler._update_photo_metadata(
            photo_folder,
            photo_id,
            f"https://example.com/photo/{photo_id}",
            title="测试套图标题",
            total_pages=3
        )
        
        # 验证元数据文件存在
        metadata_path = os.path.join(photo_folder, 'metadata.json')
        assert os.path.exists(metadata_path), "元数据文件应该存在"
        
        # 验证元数据内容
        assert metadata['photo_id'] == photo_id
        assert metadata['title'] == "测试套图标题"
        assert metadata['total_pages'] == 3
        assert metadata['images_downloaded'] == 5
        assert len(metadata['image_files']) == 5
        
        print("✓ 元数据创建成功")
        print(f"  - 套图ID: {metadata['photo_id']}")
        print(f"  - 标题: {metadata['title']}")
        print(f"  - 图片数量: {metadata['images_downloaded']}")
        print()


def test_metadata_loading():
    """测试元数据加载功能"""
    print("=" * 60)
    print("测试 2: 元数据加载（断点续传）")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        config = Config()
        config.OUTPUT_DIR = temp_dir
        crawler = ImageCrawler(config)
        
        photo_id = "test_photo_456"
        photo_folder = os.path.join(temp_dir, photo_id)
        os.makedirs(photo_folder)
        
        # 创建元数据文件
        metadata = {
            'photo_id': photo_id,
            'title': '已存在的套图',
            'photo_url': 'https://example.com/photo/test',
            'total_pages': 5,
            'images_downloaded': 10,
            'image_files': ['img1.jpg', 'img2.jpg'],
            'download_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        metadata_path = os.path.join(photo_folder, 'metadata.json')
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        # 加载元数据
        loaded_metadata = crawler._load_photo_metadata(photo_folder)
        
        assert loaded_metadata is not None, "应该能够加载元数据"
        assert loaded_metadata['photo_id'] == photo_id
        assert loaded_metadata['title'] == '已存在的套图'
        assert loaded_metadata['images_downloaded'] == 10
        
        print("✓ 元数据加载成功")
        print(f"  - 套图ID: {loaded_metadata['photo_id']}")
        print(f"  - 标题: {loaded_metadata['title']}")
        print(f"  - 已下载图片: {loaded_metadata['images_downloaded']}")
        print()


def test_download_summary():
    """测试下载摘要生成"""
    print("=" * 60)
    print("测试 3: 下载摘要生成")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        config = Config()
        config.OUTPUT_DIR = temp_dir
        config.LIST_PAGES = 2
        crawler = ImageCrawler(config)
        
        # 模拟一些套图数据
        crawler.photo_sets = [
            {
                'title': '套图1',
                'photo_id': 'photo001',
                'photo_url': 'https://example.com/photo/001',
                'status': 'success',
                'images_count': 50,
                'images_failed': 2,
                'total_pages': 3,
                'duration_seconds': 120
            },
            {
                'title': '套图2',
                'photo_id': 'photo002',
                'photo_url': 'https://example.com/photo/002',
                'status': 'success',
                'images_count': 30,
                'images_failed': 0,
                'total_pages': 2,
                'duration_seconds': 90
            },
            {
                'title': '套图3',
                'photo_id': 'photo003',
                'photo_url': 'https://example.com/photo/003',
                'status': 'failed',
                'images_count': 0,
                'error': '下载失败',
                'duration_seconds': 30
            }
        ]
        
        crawler.stats['photos_found'] = 3
        crawler.stats['images_downloaded'] = 78
        crawler.stats['images_failed'] = 5
        crawler.stats['images_skipped'] = 10
        
        # 生成摘要
        summary_path = crawler._generate_download_summary()
        
        assert summary_path is not None, "应该生成摘要文件"
        assert os.path.exists(summary_path), "摘要文件应该存在"
        
        # 验证摘要内容
        with open(summary_path, 'r', encoding='utf-8') as f:
            summary = json.load(f)
        
        assert summary['photo_sets_found'] == 3
        assert summary['photo_sets_downloaded'] == 2
        assert summary['photo_sets_failed'] == 1
        assert summary['total_images_downloaded'] == 78
        assert summary['total_images_failed'] == 5
        assert len(summary['photos']) == 3
        
        print("✓ 下载摘要生成成功")
        print(f"  - 摘要文件: {summary_path}")
        print(f"  - 套图总数: {summary['photo_sets_found']}")
        print(f"  - 成功: {summary['photo_sets_downloaded']}")
        print(f"  - 失败: {summary['photo_sets_failed']}")
        print(f"  - 图片总数: {summary['total_images_downloaded']}")
        
        # 检查文本摘要
        text_summary_path = os.path.join(temp_dir, 'download_summary.txt')
        assert os.path.exists(text_summary_path), "文本摘要应该存在"
        print(f"  - 文本摘要: {text_summary_path}")
        print()


def test_failed_downloads_tracking():
    """测试失败下载记录"""
    print("=" * 60)
    print("测试 4: 失败下载记录")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        config = Config()
        config.OUTPUT_DIR = temp_dir
        crawler = ImageCrawler(config)
        
        photo_id = "test_photo_789"
        
        # 记录失败下载
        crawler.failed_downloads[photo_id] = [
            {
                'url': 'https://example.com/img1.jpg',
                'filename': 'hash1.jpg',
                'reason': '403 Forbidden',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            },
            {
                'url': 'https://example.com/img2.jpg',
                'filename': 'hash2.jpg',
                'reason': 'Timeout',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        ]
        
        # 创建套图目录并更新元数据
        photo_folder = os.path.join(temp_dir, photo_id)
        os.makedirs(photo_folder)
        
        metadata = crawler._update_photo_metadata(
            photo_folder,
            photo_id,
            f"https://example.com/photo/{photo_id}",
            title="测试失败记录"
        )
        
        assert 'failed_images' in metadata
        assert len(metadata['failed_images']) == 2
        assert metadata['images_failed'] == 2
        
        print("✓ 失败下载记录成功")
        print(f"  - 失败数量: {metadata['images_failed']}")
        print(f"  - 失败记录: {len(metadata['failed_images'])}")
        print()


def main():
    """运行所有测试"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 15 + "元数据功能测试" + " " * 29 + "║")
    print("╚" + "=" * 58 + "╝")
    print()
    
    try:
        test_metadata_creation()
        test_metadata_loading()
        test_download_summary()
        test_failed_downloads_tracking()
        
        print("=" * 60)
        print("✓ 所有测试通过！")
        print("=" * 60)
        print()
        print("元数据功能验证成功，包括:")
        print("  1. 元数据创建和保存")
        print("  2. 元数据加载（断点续传）")
        print("  3. 下载摘要生成")
        print("  4. 失败下载记录")
        print()
        return 0
        
    except AssertionError as e:
        print(f"\n✗ 测试失败: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ 测试出错: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())
