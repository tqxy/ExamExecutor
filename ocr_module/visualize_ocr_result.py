#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OCR结果可视化工具（增强版）
支持LaTeX公式可视化
"""

import cv2
import numpy as np
import json
import os
import argparse
import sys
from PIL import Image, ImageDraw, ImageFont

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    # 导入LaTeX转换器
    from latex_to_image.latex_converter import LaTeXConverter
    LATEX_AVAILABLE = True
    latex_converter = LaTeXConverter(dpi=200, fontsize=16, figsize=(4, 1))
except ImportError:
    print("警告: 无法导入LaTeX转换器，将使用简化版本")
    LATEX_AVAILABLE = False
    latex_converter = None


def load_ocr_result(result_file):
    """加载OCR结果"""
    with open(result_file, 'r', encoding='utf-8') as f:
        content = f.read()
        # 提取结果部分
        result_str = content.split(':', 1)[1].strip()
        result = eval(result_str)  # 注意：在生产环境中应使用json.loads()或ast.literal_eval()
    return result


def draw_text_boxes(image, boxes, texts, scores, color=(0, 255, 0)):
    """在图像上绘制文本框"""
    for i, (box, text, score) in enumerate(zip(boxes, texts, scores)):
        # 转换box格式
        points = np.array(box, dtype=np.int32)
        
        # 绘制边界框
        cv2.polylines(image, [points], isClosed=True, color=color, thickness=2)
        
        # 在框附近添加文本和置信度
        x, y = points[0]
        cv2.putText(image, f"{text[:10]}({score:.2f})", (x, y-10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)


def draw_formulas(image, formulas, color=(255, 0, 0)):
    """在图像上标记公式位置并渲染LaTeX公式"""
    # 在图像顶部添加公式信息
    y_offset = 30
    for i, formula in enumerate(formulas):
        latex = formula.get('latex', '')
        text = formula.get('text', '')
        confidence = formula.get('confidence', 0)
        
        # 如果有LaTeX转换器，尝试渲染公式图像
        if LATEX_AVAILABLE and latex_converter and latex:
            try:
                # 生成LaTeX公式图像
                formula_img = latex_converter.latex_to_image(latex)
                if formula_img:
                    # 转换PIL图像到OpenCV格式
                    formula_img_cv = cv2.cvtColor(np.array(formula_img), cv2.COLOR_RGB2BGR)
                    
                    # 调整公式图像大小
                    max_width = min(formula_img_cv.shape[1], image.shape[1] - 20)
                    max_height = 100  # 限制高度
                    
                    if formula_img_cv.shape[1] > max_width or formula_img_cv.shape[0] > max_height:
                        scale_x = max_width / formula_img_cv.shape[1]
                        scale_y = max_height / formula_img_cv.shape[0]
                        scale = min(scale_x, scale_y)
                        new_width = int(formula_img_cv.shape[1] * scale)
                        new_height = int(formula_img_cv.shape[0] * scale)
                        formula_img_cv = cv2.resize(formula_img_cv, (new_width, new_height))
                    
                    # 在主图像上放置公式图像
                    x_pos = 10
                    if y_offset + formula_img_cv.shape[0] < image.shape[0]:
                        image[y_offset:y_offset+formula_img_cv.shape[0], 
                              x_pos:x_pos+formula_img_cv.shape[1]] = formula_img_cv
                        
                        # 添加置信度信息
                        cv2.putText(image, f"Confidence: {confidence:.2f}", 
                                   (x_pos, y_offset + formula_img_cv.shape[0] + 20), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
                        
                        y_offset += formula_img_cv.shape[0] + 30
                    else:
                        # 如果空间不足，只显示文本信息
                        cv2.putText(image, f"Formula {i+1}: {text[:20]}... ({confidence:.2f})", (10, y_offset), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                        y_offset += 30
                else:
                    # 如果无法生成图像，显示文本信息
                    cv2.putText(image, f"Formula {i+1}: {text[:20]}... ({confidence:.2f})", (10, y_offset), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                    y_offset += 30
            except Exception as e:
                print(f"渲染公式时出错: {e}")
                # 出错时显示文本信息
                cv2.putText(image, f"Formula {i+1}: {text[:20]}... ({confidence:.2f})", (10, y_offset), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                y_offset += 30
        else:
            # 没有LaTeX转换器时显示文本信息
            cv2.putText(image, f"Formula {i+1}: {text[:20]}... ({confidence:.2f})", (10, y_offset), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            y_offset += 30


def visualize_ocr_result(image_path, result_file, output_path=None):
    """可视化OCR结果"""
    # 加载原始图像
    image = cv2.imread(image_path)
    if image is None:
        print(f"无法加载图像: {image_path}")
        return False
    
    # 加载OCR结果
    try:
        result = load_ocr_result(result_file)
    except Exception as e:
        print(f"加载OCR结果失败: {e}")
        return False
    
    # 获取PaddleOCR结果
    paddle_result = result.get('paddleocr_result', {})
    text_recognition = paddle_result.get('text_recognition', {})
    
    # 绘制文本框
    boxes = text_recognition.get('boxes', [])
    texts = text_recognition.get('texts', [])
    scores = text_recognition.get('scores', [])
    
    if boxes and texts and scores:
        draw_text_boxes(image, boxes, texts, scores)
    
    # 绘制公式
    formulas = result.get('formulas', [])
    if formulas:
        draw_formulas(image, formulas)
    
    # 添加综合信息
    combined_text = result.get('combined_text', '')
    confidence_score = result.get('confidence_score', 0)
    
    cv2.putText(image, f"Combined Confidence: {confidence_score:.2f}", (10, image.shape[0] - 30), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
    
    # 保存或显示结果
    if output_path:
        cv2.imwrite(output_path, image)
        print(f"可视化结果已保存到: {output_path}")
    else:
        # 显示图像
        cv2.imshow('OCR Result Visualization', image)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    
    return True


def main():
    parser = argparse.ArgumentParser(description='OCR结果可视化工具')
    parser.add_argument('--image', '-i', type=str, required=True, help='原始图像文件路径')
    parser.add_argument('--result', '-r', type=str, required=True, help='OCR结果文件路径')
    parser.add_argument('--output', '-o', type=str, help='输出图像文件路径（可选）')
    
    args = parser.parse_args()
    
    success = visualize_ocr_result(args.image, args.result, args.output)
    if success:
        print("OCR结果可视化完成!")
    else:
        print("OCR结果可视化失败!")
        return 1
    
    return 0


if __name__ == "__main__":
    main()