#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OCR组合处理核心模块
集成Pix2Text和Paddle OCR，实现优势互补的OCR处理方案
"""

import logging
from typing import Dict, Any, Optional
from enum import Enum

from ..pix2text.processor import Pix2TextProcessor
from ..paddleocr.processor import PaddleOCRProcessor
from ..utils.result_combiner import combine_results

# 配置日志
logger = logging.getLogger(__name__)


class OCRMode(Enum):
    """OCR处理模式枚举"""
    PIX2TEXT_ONLY = "pix2text_only"
    PADDLE_OCR_ONLY = "paddleocr_only"
    COMBINED = "combined"


class OCRProcessor:
    """OCR组合处理器类，集成Pix2Text和Paddle OCR"""
    
    def __init__(self, pix2text_config: Optional[Dict[str, Any]] = None, 
                 paddleocr_config: Optional[Dict[str, Any]] = None):
        """
        初始化OCR组合处理器
        
        Args:
            pix2text_config: Pix2Text配置参数
            paddleocr_config: Paddle OCR配置参数
        """
        # 初始化Pix2Text处理器
        self.pix2text_processor = Pix2TextProcessor(pix2text_config)
        
        # 初始化Paddle OCR处理器
        self.paddleocr_processor = PaddleOCRProcessor(paddleocr_config)
        
        logger.info("OCR组合处理器初始化成功")
    
    def process_image(self, image_path: str, mode: OCRMode = OCRMode.COMBINED) -> Dict[str, Any]:
        """
        处理图像，根据指定模式使用不同的OCR引擎
        
        Args:
            image_path: 图像文件路径
            mode: OCR处理模式
            
        Returns:
            包含识别结果的字典
        """
        try:
            if mode == OCRMode.PIX2TEXT_ONLY:
                result = self._process_with_pix2text(image_path)
            elif mode == OCRMode.PADDLE_OCR_ONLY:
                result = self._process_with_paddleocr(image_path)
            else:  # COMBINED模式
                result = self._process_combined(image_path)
            
            logger.info(f"图像处理完成: {image_path}, 模式: {mode.value}")
            return result
        except Exception as e:
            logger.error(f"图像处理失败: {e}")
            raise
    
    def _process_with_pix2text(self, image_path: str) -> Dict[str, Any]:
        """
        使用Pix2Text单独处理图像
        
        Args:
            image_path: 图像文件路径
            
        Returns:
            Pix2Text识别结果
        """
        logger.info(f"使用Pix2Text处理图像: {image_path}")
        return self.pix2text_processor.process_image(image_path)
    
    def _process_with_paddleocr(self, image_path: str) -> Dict[str, Any]:
        """
        使用Paddle OCR单独处理图像
        
        Args:
            image_path: 图像文件路径
            
        Returns:
            Paddle OCR识别结果
        """
        logger.info(f"使用Paddle OCR处理图像: {image_path}")
        return self.paddleocr_processor.process_image(image_path)
    
    def _process_combined(self, image_path: str) -> Dict[str, Any]:
        """
        组合使用Pix2Text和Paddle OCR处理图像
        
        Args:
            image_path: 图像文件路径
            
        Returns:
            组合识别结果
        """
        logger.info(f"组合使用Pix2Text和Paddle OCR处理图像: {image_path}")
        
        # 分别获取两种OCR的结果
        pix2text_result = self.pix2text_processor.process_image(image_path)
        paddleocr_result = self.paddleocr_processor.process_image(image_path)
        
        # 组合结果
        combined_result = combine_results(pix2text_result, paddleocr_result)
        combined_result['image_path'] = image_path
        combined_result['processing_mode'] = 'combined'
        
        return combined_result
    
    def batch_process(self, image_paths: list, mode: OCRMode = OCRMode.COMBINED) -> list:
        """
        批量处理图像
        
        Args:
            image_paths: 图像文件路径列表
            mode: OCR处理模式
            
        Returns:
            处理结果列表
        """
        results = []
        for image_path in image_paths:
            try:
                result = self.process_image(image_path, mode)
                results.append(result)
            except Exception as e:
                logger.error(f"批量处理图像失败: {image_path}, 错误: {e}")
                # 添加错误信息到结果中
                results.append({
                    'image_path': image_path,
                    'error': str(e),
                    'success': False
                })
        
        return results


# 示例使用
if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(level=logging.INFO)
    
    # 创建处理器实例
    pix2text_config = {
        'device': 'cpu'
    }
    
    paddleocr_config = {
        'lang': 'ch',
        'device': 'cpu'
    }
    
    processor = OCRProcessor(pix2text_config, paddleocr_config)
    
    # 处理示例图像
    # result = processor.process_image("example.png", OCRMode.COMBINED)
    # print(result)