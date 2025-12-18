#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
结果合并工具模块
用于合并Pix2Text和Paddle OCR的识别结果
"""

import logging
from typing import Dict, Any, List
from collections import defaultdict

# 配置日志
logger = logging.getLogger(__name__)


def combine_results(pix2text_result: Dict[str, Any], paddleocr_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    合并Pix2Text和Paddle OCR的识别结果
    
    Args:
        pix2text_result: Pix2Text识别结果
        paddleocr_result: Paddle OCR识别结果
        
    Returns:
        合并后的结果字典
    """
    try:
        # 创建合并结果
        combined_result = {
            'pix2text_result': pix2text_result,
            'paddleocr_result': paddleocr_result,
            'combined_text': '',
            'formulas': [],
            'confidence_score': 0.0
        }
        
        # 提取Pix2Text的公式识别结果
        if 'formula' in pix2text_result:
            formula = pix2text_result['formula']
            if formula.get('confidence', 0) > 0.8:  # 置信度阈值
                combined_result['formulas'].append({
                    'latex': formula.get('latex', ''),
                    'text': formula.get('text', ''),
                    'source': 'pix2text',
                    'confidence': formula.get('confidence', 0)
                })
        
        # 提取Paddle OCR的文本识别结果
        paddle_texts = []
        if 'text_recognition' in paddleocr_result:
            text_recognition = paddleocr_result['text_recognition']
            texts = text_recognition.get('texts', [])
            scores = text_recognition.get('scores', [])
            
            # 合并高置信度文本
            for i, (text, score) in enumerate(zip(texts, scores)):
                if score > 0.8:  # 置信度阈值
                    paddle_texts.append(text)
        
        # 组合文本内容
        pix2text_text = pix2text_result.get('text', {}).get('text', '') if 'text' in pix2text_result else ''
        combined_text = f"{pix2text_text} {' '.join(paddle_texts)}".strip()
        combined_result['combined_text'] = combined_text
        
        # 计算综合置信度
        pix2text_confidence = pix2text_result.get('formula', {}).get('confidence', 0) if 'formula' in pix2text_result else 0
        paddleocr_confidence = max(paddleocr_result.get('text_recognition', {}).get('scores', [0]), default=0) if 'text_recognition' in paddleocr_result else 0
        combined_result['confidence_score'] = (pix2text_confidence + paddleocr_confidence) / 2
        
        logger.info("结果合并完成")
        return combined_result
    except Exception as e:
        logger.error(f"结果合并失败: {e}")
        raise


def filter_high_confidence_results(results: List[Dict[str, Any]], threshold: float = 0.8) -> List[Dict[str, Any]]:
    """
    过滤高置信度结果
    
    Args:
        results: OCR结果列表
        threshold: 置信度阈值
        
    Returns:
        过滤后的高置信度结果列表
    """
    filtered_results = []
    for result in results:
        confidence = result.get('confidence_score', 0)
        if confidence >= threshold:
            filtered_results.append(result)
    
    return filtered_results


def extract_formulas(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    从结果中提取所有公式
    
    Args:
        results: OCR结果列表
        
    Returns:
        公式列表
    """
    formulas = []
    for result in results:
        if 'formulas' in result:
            formulas.extend(result['formulas'])
    
    return formulas


def extract_texts(results: List[Dict[str, Any]]) -> List[str]:
    """
    从结果中提取所有文本
    
    Args:
        results: OCR结果列表
        
    Returns:
        文本列表
    """
    texts = []
    for result in results:
        if 'combined_text' in result:
            texts.append(result['combined_text'])
    
    return texts


# 示例使用
if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(level=logging.INFO)
    
    # 示例结果
    pix2text_result = {
        'formula': {
            'latex': '\\int_{0}^{\\infty} e^{-x^2} dx = \\frac{\\sqrt{\\pi}}{2}',
            'text': '∫₀^∞ e^(-x²) dx = √π/2',
            'confidence': 0.95
        },
        'text': {
            'text': '计算下列积分:',
            'confidence': 0.92
        }
    }
    
    paddleocr_result = {
        'text_recognition': {
            'texts': ['计算下列积分:', '示例文本2', '示例文本3'],
            'scores': [0.95, 0.87, 0.92]
        }
    }
    
    # 合并结果
    # combined = combine_results(pix2text_result, paddleocr_result)
    # print(combined)