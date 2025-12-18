#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高精度OCR处理模块主入口
集成Pix2Text和Paddle OCR的组合方案
"""

import logging
from typing import Dict, Any, List, Optional
from enum import Enum

from .core.processor import OCRProcessor, OCRMode
from .utils.result_combiner import filter_high_confidence_results, extract_formulas, extract_texts

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HighPrecisionOCR:
    """高精度OCR处理类"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化高精度OCR处理器
        
        Args:
            config: 配置参数字典
                - pix2text_config: Pix2Text配置
                - paddleocr_config: Paddle OCR配置
        """
        self.config = config or {}
        
        # 提取子模块配置
        pix2text_config = self.config.get('pix2text_config', {})
        paddleocr_config = self.config.get('paddleocr_config', {})
        
        # 初始化OCR处理器
        self.ocr_processor = OCRProcessor(pix2text_config, paddleocr_config)
        
        logger.info("高精度OCR处理器初始化成功")
    
    def process_single_image(self, image_path: str, mode: str = 'combined') -> Dict[str, Any]:
        """
        处理单张图像
        
        Args:
            image_path: 图像文件路径
            mode: 处理模式 ('pix2text_only', 'paddleocr_only', 'combined')
            
        Returns:
            OCR处理结果
        """
        try:
            # 转换模式字符串为枚举
            mode_enum = OCRMode(mode) if mode in [m.value for m in OCRMode] else OCRMode.COMBINED
            
            # 处理图像
            result = self.ocr_processor.process_image(image_path, mode_enum)
            result['success'] = True
            
            logger.info(f"单张图像处理完成: {image_path}")
            return result
        except Exception as e:
            logger.error(f"单张图像处理失败: {image_path}, 错误: {e}")
            return {
                'image_path': image_path,
                'error': str(e),
                'success': False
            }
    
    def process_batch_images(self, image_paths: List[str], mode: str = 'combined') -> List[Dict[str, Any]]:
        """
        批量处理图像
        
        Args:
            image_paths: 图像文件路径列表
            mode: 处理模式 ('pix2text_only', 'paddleocr_only', 'combined')
            
        Returns:
            OCR处理结果列表
        """
        try:
            # 转换模式字符串为枚举
            mode_enum = OCRMode(mode) if mode in [m.value for m in OCRMode] else OCRMode.COMBINED
            
            # 批量处理图像
            results = self.ocr_processor.batch_process(image_paths, mode_enum)
            
            logger.info(f"批量图像处理完成，共处理 {len(image_paths)} 张图像")
            return results
        except Exception as e:
            logger.error(f"批量图像处理失败: {e}")
            return [{
                'error': str(e),
                'success': False
            }]
    
    def process_with_filtering(self, image_paths: List[str], 
                              mode: str = 'combined', 
                              confidence_threshold: float = 0.8) -> Dict[str, Any]:
        """
        处理图像并过滤低置信度结果
        
        Args:
            image_paths: 图像文件路径列表
            mode: 处理模式
            confidence_threshold: 置信度阈值
            
        Returns:
            包含过滤结果的字典
        """
        try:
            # 处理图像
            results = self.process_batch_images(image_paths, mode)
            
            # 过滤高置信度结果
            high_confidence_results = filter_high_confidence_results(results, confidence_threshold)
            
            # 提取公式和文本
            formulas = extract_formulas(high_confidence_results)
            texts = extract_texts(high_confidence_results)
            
            return {
                'all_results': results,
                'high_confidence_results': high_confidence_results,
                'filtered_count': len(results) - len(high_confidence_results),
                'formulas': formulas,
                'texts': texts,
                'success': True
            }
        except Exception as e:
            logger.error(f"带过滤的图像处理失败: {e}")
            return {
                'error': str(e),
                'success': False
            }


# 示例使用和测试函数
def demo():
    """演示函数"""
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
    
    # 创建处理器实例
    ocr = HighPrecisionOCR(config)
    
    # 处理示例（这里只是演示，实际使用时需要真实的图像路径）
    # result = ocr.process_single_image("example.png", "combined")
    # print(result)


if __name__ == "__main__":
    demo()