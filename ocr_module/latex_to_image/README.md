# LaTeX to Image 转换模块

这是一个专门用于将LaTeX公式转换为图像的Python模块。

## 功能特点

1. 支持单个LaTeX公式转换为图像
2. 支持批量LaTeX公式转换
3. 可以直接从OCR结果中提取LaTeX公式并转换
4. 高质量图像输出，可自定义分辨率和尺寸

## 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

### 1. 单个公式转换

```python
from latex_converter import convert_single_formula

# 转换公式并保存为文件
success = convert_single_formula(r"\int_{0}^{\infty} e^{-x^2} dx = \frac{\sqrt{\pi}}{2}", "output.png")

# 转换公式并获取图像对象
image = convert_single_formula(r"E = mc^2")
if image:
    image.show()  # 显示图像
```

### 2. 批量公式转换

```python
from latex_converter import LaTeXConverter

converter = LaTeXConverter()

formulas = [
    r"E = mc^2",
    r"\sum_{i=1}^{n} x_i = \frac{n(n+1)}{2}",
    r"\lim_{x \to \infty} \frac{1}{x} = 0"
]

results = converter.batch_convert(formulas, "output_directory")
```

### 3. 从OCR结果转换

```python
from latex_converter import convert_from_ocr_result

# 从OCR结果文件中提取公式并转换
results = convert_from_ocr_result("../ocr_module/test_image_ocr_result.txt", "formulas_output")
```

## API说明

### LaTeXConverter 类

#### 构造函数
```python
LaTeXConverter(dpi=300, fontsize=16, figsize=(6, 2))
```

参数:
- `dpi`: 图像分辨率，默认300
- `fontsize`: 字体大小，默认16
- `figsize`: 图像尺寸，默认(6, 2)

#### 方法

##### latex_to_image(latex_str, output_path=None)
将LaTeX公式转换为图像

参数:
- `latex_str`: LaTeX公式字符串
- `output_path`: 输出图像路径，如果为None则返回图像对象

返回:
- 如果output_path为None返回PIL.Image对象，否则返回是否成功(bool)

##### batch_convert(latex_list, output_dir)
批量转换LaTeX公式为图像

参数:
- `latex_list`: LaTeX公式字符串列表
- `output_dir`: 输出目录

返回:
- 转换结果字典

### 便捷函数

##### convert_single_formula(latex_str, output_path=None)
快速转换单个LaTeX公式

##### convert_from_ocr_result(ocr_result_path, output_dir)
从OCR结果中提取LaTeX公式并转换为图像

## 测试

运行测试脚本:
```bash
python test_converter.py
```