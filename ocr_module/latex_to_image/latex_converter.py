"""
LaTeX 公式转图像模块
"""

import matplotlib.pyplot as plt
import matplotlib as mpl
from PIL import Image
import io
import numpy as np
import os

class LaTeXConverter:
    """LaTeX 公式转图像转换器"""
    
    def __init__(self, dpi=300, fontsize=16, figsize=(6, 2)):
        """
        初始化转换器
        
        Args:
            dpi (int): 图像分辨率
            fontsize (int): 字体大小
            figsize (tuple): 图像尺寸
        """
        self.dpi = dpi
        self.fontsize = fontsize
        self.figsize = figsize
        
        # 设置matplotlib后端
        mpl.use('Agg')
        
        # 配置matplotlib
        plt.rcParams.update({
            "text.usetex": False,  # 不使用LaTeX渲染，使用matplotlib内置渲染
            "font.family": "serif",
            "font.serif": ["Computer Modern Roman"],
        })
    
    def latex_to_image(self, latex_str, output_path=None):
        """
        将LaTeX公式转换为图像
        
        Args:
            latex_str (str): LaTeX公式字符串
            output_path (str): 输出图像路径，如果为None则返回图像对象
            
        Returns:
            PIL.Image or bool: 如果output_path为None返回图像对象，否则返回是否成功
        """
        try:
            # 创建图形
            fig = plt.figure(figsize=self.figsize, dpi=self.dpi)
            ax = fig.add_axes([0, 0, 1, 1])
            
            # 移除坐标轴
            ax.set_axis_off()
            
            # 渲染LaTeX公式
            ax.text(0.5, 0.5, f"${latex_str}$", 
                   horizontalalignment='center',
                   verticalalignment='center',
                   fontsize=self.fontsize,
                   transform=ax.transAxes)
            
            # 保存或返回图像
            if output_path:
                plt.savefig(output_path, 
                           bbox_inches='tight', 
                           pad_inches=0.1,
                           dpi=self.dpi,
                           transparent=False,
                           facecolor='white')
                plt.close(fig)
                return os.path.exists(output_path)
            else:
                # 保存到内存缓冲区
                buf = io.BytesIO()
                plt.savefig(buf, 
                           bbox_inches='tight', 
                           pad_inches=0.1,
                           dpi=self.dpi,
                           format='png',
                           transparent=False,
                           facecolor='white')
                buf.seek(0)
                img = Image.open(buf)
                img_copy = img.copy()  # 创建副本以避免关闭缓冲区时出现问题
                buf.close()
                plt.close(fig)
                return img_copy
                
        except Exception as e:
            print(f"转换LaTeX公式时出错: {e}")
            if 'fig' in locals():
                plt.close(fig)
            return None if output_path is None else False
    
    def batch_convert(self, latex_list, output_dir):
        """
        批量转换LaTeX公式为图像
        
        Args:
            latex_list (list): LaTeX公式字符串列表
            output_dir (str): 输出目录
            
        Returns:
            dict: 转换结果字典
        """
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
        
        results = {}
        for i, latex_str in enumerate(latex_list):
            output_path = os.path.join(output_dir, f"formula_{i+1}.png")
            success = self.latex_to_image(latex_str, output_path)
            results[f"formula_{i+1}"] = {
                "latex": latex_str,
                "output_path": output_path if success else None,
                "success": success
            }
        
        return results

def convert_single_formula(latex_str, output_path=None):
    """
    快速转换单个LaTeX公式
    
    Args:
        latex_str (str): LaTeX公式字符串
        output_path (str): 输出图像路径
        
    Returns:
        PIL.Image or bool: 如果output_path为None返回图像对象，否则返回是否成功
    """
    converter = LaTeXConverter()
    return converter.latex_to_image(latex_str, output_path)

def convert_from_ocr_result(ocr_result_path, output_dir):
    """
    从OCR结果中提取LaTeX公式并转换为图像
    
    Args:
        ocr_result_path (str): OCR结果文件路径
        output_dir (str): 输出目录
        
    Returns:
        dict: 转换结果
    """
    import ast
    
    try:
        # 读取OCR结果
        with open(ocr_result_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 提取字典部分
        dict_start = content.find('{')
        dict_end = content.rfind('}') + 1
        if dict_start != -1 and dict_end > dict_start:
            dict_str = content[dict_start:dict_end]
            # 使用ast.literal_eval安全地解析Python字典
            ocr_result = ast.literal_eval(dict_str)
        else:
            raise ValueError("未找到有效的字典内容")
        
        # 提取公式
        formulas = []
        # 从pix2text结果中提取
        if 'pix2text_result' in ocr_result:
            formula_data = ocr_result['pix2text_result'].get('formula', {})
            if 'latex' in formula_data:
                # 修复双重转义的LaTeX字符串
                latex_str = formula_data['latex'].replace('\\\\', '\\')
                formulas.append(latex_str)
        
        # 从formulas数组中提取
        if 'formulas' in ocr_result:
            for formula in ocr_result['formulas']:
                if 'latex' in formula:
                    # 修复双重转义的LaTeX字符串
                    latex_str = formula['latex'].replace('\\\\', '\\')
                    formulas.append(latex_str)
        
        if not formulas:
            print("未找到LaTeX公式")
            return {}
        
        # 转换公式
        converter = LaTeXConverter()
        results = converter.batch_convert(formulas, output_dir)
        
        return results
        
    except Exception as e:
        print(f"从OCR结果转换时出错: {e}")
        return {}

if __name__ == "__main__":
    # 测试代码
    converter = LaTeXConverter()
    
    # 示例LaTeX公式
    test_formulas = [
        r"\int_{0}^{\infty} e^{-x^2} dx = \frac{\sqrt{\pi}}{2}",
        r"E = mc^2",
        r"\sum_{i=1}^{n} x_i = \frac{n(n+1)}{2}",
        r"\lim_{x \to \infty} \frac{1}{x} = 0"
    ]
    
    # 批量转换 - 使用明确的输出目录
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "direct_test_output")
    results = converter.batch_convert(test_formulas, output_dir)
    
    # 打印结果
    for name, result in results.items():
        print(f"{name}: {'成功' if result['success'] else '失败'}")
        if result['success']:
            print(f"  LaTeX: {result['latex']}")
            print(f"  路径: {result['output_path']}")