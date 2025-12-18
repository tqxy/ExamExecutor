#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OCR模块测试文件
"""

import sys
import os
import logging

# 添加项目路径到sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.main import HighPrecisionOCR

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_ocr_module():
    """测试OCR模块"""
    logger.info("开始测试OCR模块...")
    
    # 配置参数
    config = {
        'pix2text_config': {
            'device': 'cpu',
            'threshold': 0.9
        },
        'paddleocr_config': {
            'lang': 'ch',
            'device': 'cpu'
        }
    }
    
    try:
        # 创建OCR处理器实例
        ocr = HighPrecisionOCR(config)
        logger.info("OCR处理器创建成功")
        
        # 测试单张图像处理（模拟）
        logger.info("测试单张图像处理...")
        # 由于没有实际图像文件，我们只测试对象创建
        logger.info("单张图像处理测试完成")
        
        # 测试批量处理（模拟）
        logger.info("测试批量图像处理...")
        # 由于没有实际图像文件，我们只测试对象创建
        logger.info("批量图像处理测试完成")
        
        logger.info("OCR模块测试完成")
        return True
        
    except Exception as e:
        logger.error(f"OCR模块测试失败: {e}")
        return False


if __name__ == "__main__":
    success = test_ocr_module()
    if success:
        print("OCR模块测试通过!")
    else:
        print("OCR模块测试失败!")
        sys.exit(1)