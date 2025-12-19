"""
LaTeX to Image 转换模块测试脚本
"""

import os
import sys

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from latex_converter import LaTeXConverter, convert_single_formula, convert_from_ocr_result

def test_single_conversion():
    """测试单个公式转换"""
    print("测试单个公式转换...")
    
    # 创建转换器
    converter = LaTeXConverter()
    
    # 测试公式
    latex_formula = r"\int_{0}^{\infty} e^{-x^2} dx = \frac{\sqrt{\pi}}{2}"
    
    # 转换为图像文件
    output_path = "test_formula.png"
    success = converter.latex_to_image(latex_formula, output_path)
    
    if success:
        print(f"公式转换成功，图像保存至: {output_path}")
        return True
    else:
        print("公式转换失败")
        return False

def test_batch_conversion():
    """测试批量公式转换"""
    print("\n测试批量公式转换...")
    
    # 创建转换器
    converter = LaTeXConverter()
    
    # 测试公式列表
    formulas = [
        r"E = mc^2",
        r"\sum_{i=1}^{n} x_i = \frac{n(n+1)}{2}",
        r"\lim_{x \to \infty} \frac{1}{x} = 0",
        r"\sqrt{a^2 + b^2} = c"
    ]
    
    # 批量转换
    output_dir = "batch_output"
    results = converter.batch_convert(formulas, output_dir)
    
    # 打印结果
    success_count = 0
    for name, result in results.items():
        if result['success']:
            success_count += 1
            print(f"{name}: 成功 - {result['output_path']}")
        else:
            print(f"{name}: 失败")
    
    print(f"\n批量转换完成: {success_count}/{len(formulas)} 成功")
    return success_count == len(formulas)

def test_from_ocr_result():
    """测试从OCR结果转换"""
    print("\n测试从OCR结果转换...")
    
    # OCR结果文件路径
    ocr_result_path = os.path.join("..", "test_image_ocr_result.txt")
    
    # 检查文件是否存在
    if not os.path.exists(ocr_result_path):
        # 尝试另一种路径
        ocr_result_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "test_image_ocr_result.txt")
        if not os.path.exists(ocr_result_path):
            print(f"OCR结果文件不存在: {ocr_result_path}")
            return False
    
    # 转换目录 - 使用与测试脚本相同的目录
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ocr_formulas")
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 从OCR结果转换
    results = convert_from_ocr_result(ocr_result_path, output_dir)
    
    if not results:
        print("未找到可转换的LaTeX公式")
        return False
    
    # 打印结果
    success_count = 0
    for name, result in results.items():
        if result['success']:
            success_count += 1
            print(f"{name}: 成功 - {result['output_path']}")
        else:
            print(f"{name}: 失败")
    
    print(f"\nOCR结果转换完成: {success_count}/{len(results)} 成功")
    return success_count > 0

def main():
    """主测试函数"""
    print("LaTeX to Image 转换模块测试")
    print("=" * 40)
    
    # 运行所有测试
    tests = [
        test_single_conversion,
        test_batch_conversion,
        test_from_ocr_result
    ]
    
    passed = 0
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"测试 {test.__name__} 发生错误: {e}")
    
    print("\n" + "=" * 40)
    print(f"测试完成: {passed}/{len(tests)} 通过")
    
    if passed == len(tests):
        print("所有测试通过!")
        return True
    else:
        print("部分测试失败!")
        return False

if __name__ == "__main__":
    main()