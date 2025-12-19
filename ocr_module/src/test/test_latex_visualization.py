#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LaTeX公式可视化测试脚本
"""

import os
import sys
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from latex_to_image.latex_converter import LaTeXConverter, convert_single_formula
    LATEX_AVAILABLE = True
except ImportError:
    print("警告: 无法导入LaTeX转换器")
    LATEX_AVAILABLE = False

def create_test_formulas_image():
    """创建包含多个LaTeX公式的测试图像"""
    if not LATEX_AVAILABLE:
        print("LaTeX转换器不可用")
        return False
    
    # 测试公式列表
    test_formulas = [
        r"\int_{0}^{\infty} e^{-x^2} dx = \frac{\sqrt{\pi}}{2}",
        r"E = mc^2",
        r"\sum_{i=1}^{n} x_i = \frac{n(n+1)}{2}",
        r"\lim_{x \to \infty} \frac{1}{x} = 0",
        r"\frac{d}{dx}\left(\int_{0}^{x} f(t) dt\right) = f(x)",
        r"\vec{F} = m\vec{a}",
        r"\nabla \cdot \vec{E} = \frac{\rho}{\varepsilon_0}",
        r"\sigma = \frac{F}{A}"
    ]
    
    # 创建一个大的白色背景图像
    width, height = 800, 1000
    image = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(image)
    
    # 尝试使用中文字体
    try:
        font = ImageFont.truetype("simhei.ttf", 24)
    except:
        font = ImageFont.load_default()
    
    # 在图像上添加标题
    draw.text((20, 20), "LaTeX公式可视化测试", fill='black', font=font)
    
    # 创建LaTeX转换器
    converter = LaTeXConverter(dpi=150, fontsize=14, figsize=(6, 1.5))
    
    # 在图像上放置公式
    y_offset = 80
    for i, formula in enumerate(test_formulas):
        try:
            # 生成LaTeX公式图像
            formula_img = converter.latex_to_image(formula)
            if formula_img:
                # 调整公式图像大小
                max_width = width - 40
                if formula_img.width > max_width:
                    scale = max_width / formula_img.width
                    new_width = int(formula_img.width * scale)
                    new_height = int(formula_img.height * scale)
                    formula_img = formula_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # 在主图像上粘贴公式图像
                if y_offset + formula_img.height < height - 50:
                    image.paste(formula_img, (20, y_offset))
                    y_offset += formula_img.height + 20
                else:
                    break
            else:
                # 如果无法生成图像，显示文本
                draw.text((20, y_offset), f"公式 {i+1}: {formula}", fill='black', font=font)
                y_offset += 40
        except Exception as e:
            print(f"处理公式 {formula} 时出错: {e}")
            draw.text((20, y_offset), f"公式 {i+1}: {formula}", fill='black', font=font)
            y_offset += 40
    
    # 保存图像
    output_path = "test_formulas_image.png"
    image.save(output_path)
    print(f"测试公式图像已保存到: {output_path}")
    return True

def main():
    """主函数"""
    print("开始LaTeX公式可视化测试...")
    
    # 创建测试公式图像
    if create_test_formulas_image():
        print("测试完成!")
    else:
        print("测试失败!")

if __name__ == "__main__":
    main()