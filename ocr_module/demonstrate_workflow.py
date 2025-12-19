#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OCR完整流程演示脚本
展示从图像处理到结果可视化的完整流程
"""

import os
import sys
import json
import cv2
import numpy as np

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    # 导入OCR模块
    from src.main import OCRProcessor
    # 导入LaTeX转换器
    from latex_to_image.latex_converter import LaTeXConverter
    MODULES_AVAILABLE = True
except ImportError as e:
    print(f"警告: 无法导入必要模块: {e}")
    MODULES_AVAILABLE = False

def create_demo_image():
    """创建演示图像"""
    # 创建一个白色背景图像
    width, height = 600, 400
    image = np.ones((height, width, 3), dtype=np.uint8) * 255
    
    # 添加一些示例文本
    cv2.putText(image, "OCR Processing Demo", (50, 50), 
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    cv2.putText(image, "Sample Text 1", (50, 100), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 1)
    cv2.putText(image, "Sample Text 2", (50, 150), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 1)
    
    # 添加一个模拟公式区域
    cv2.rectangle(image, (50, 200), (550, 250), (255, 0, 0), 2)
    cv2.putText(image, "Formula Area", (60, 230), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 1)
    
    # 保存图像
    demo_image_path = "demo_image.png"
    cv2.imwrite(demo_image_path, image)
    print(f"演示图像已保存到: {demo_image_path}")
    return demo_image_path

def create_sample_ocr_result():
    """创建示例OCR结果"""
    sample_result = {
        'pix2text_result': {
            'formula': {
                'latex': '\\int_{0}^{\\infty} e^{-x^2} dx = \\frac{\\sqrt{\\pi}}{2}',
                'confidence': 0.95,
                'text': '∫₀^∞ e^(-x²) dx = √π/2'
            },
            'text': {
                'text': '这是一个示例文本',
                'confidence': 0.92
            },
            'image_path': 'demo_image.png'
        },
        'paddleocr_result': {
            'text_recognition': {
                'texts': ['示例文本1', '示例文本2', '示例文本3'],
                'boxes': [
                    [[50, 80], [200, 80], [200, 110], [50, 110]],
                    [[50, 130], [200, 130], [200, 160], [50, 160]],
                    [[50, 180], [200, 180], [200, 210], [50, 210]]
                ],
                'scores': [0.95, 0.87, 0.92]
            },
            'table_recognition': {
                'table_structure': '[[1, 2, 3], [4, 5, 6], [7, 8, 9]]',
                'confidence': 0.89
            },
            'image_path': 'demo_image.png'
        },
        'combined_text': '这是一个示例文本 示例文本1 示例文本2 示例文本3',
        'formulas': [
            {
                'latex': '\\int_{0}^{\\infty} e^{-x^2} dx = \\frac{\\sqrt{\\pi}}{2}',
                'text': '∫₀^∞ e^(-x²) dx = √π/2',
                'source': 'pix2text',
                'confidence': 0.95
            }
        ],
        'confidence_score': 0.95,
        'image_path': 'demo_image.png',
        'processing_mode': 'combined',
        'success': True
    }
    
    # 保存结果到文件
    result_file = "demo_ocr_result.txt"
    with open(result_file, 'w', encoding='utf-8') as f:
        f.write("OCR处理结果:\n")
        f.write(str(sample_result))
    
    print(f"示例OCR结果已保存到: {result_file}")
    return result_file

def demonstrate_complete_workflow():
    """演示完整的OCR工作流程"""
    print("=" * 50)
    print("OCR完整流程演示")
    print("=" * 50)
    
    # 1. 创建演示图像
    print("步骤1: 创建演示图像...")
    demo_image_path = create_demo_image()
    
    # 2. 创建示例OCR结果
    print("步骤2: 创建示例OCR结果...")
    result_file = create_sample_ocr_result()
    
    # 3. 可视化结果
    print("步骤3: 可视化OCR结果...")
    try:
        # 使用现有的可视化工具
        from visualize_ocr_result import visualize_ocr_result
        output_path = "demo_visualization_result.png"
        success = visualize_ocr_result(demo_image_path, result_file, output_path)
        if success:
            print(f"可视化结果已保存到: {output_path}")
        else:
            print("可视化失败")
    except Exception as e:
        print(f"可视化过程中出错: {e}")
    
    # 4. 展示LaTeX公式转换功能
    print("步骤4: 展示LaTeX公式转换功能...")
    if MODULES_AVAILABLE:
        try:
            converter = LaTeXConverter(dpi=200, fontsize=16, figsize=(6, 2))
            test_formula = r"\int_{0}^{\infty} e^{-x^2} dx = \frac{\sqrt{\pi}}{2}"
            formula_image_path = "demo_formula.png"
            success = converter.latex_to_image(test_formula, formula_image_path)
            if success:
                print(f"LaTeX公式图像已保存到: {formula_image_path}")
            else:
                print("LaTeX公式转换失败")
        except Exception as e:
            print(f"LaTeX转换过程中出错: {e}")
    else:
        print("所需模块不可用，跳过LaTeX转换演示")
    
    print("\n" + "=" * 50)
    print("演示完成!")
    print("=" * 50)

def main():
    """主函数"""
    demonstrate_complete_workflow()

if __name__ == "__main__":
    main()