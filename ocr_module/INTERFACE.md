# 高精度OCR处理模块接口定义

## 1. 概述

本文档定义了高精度OCR处理模块的公共接口，包括类、方法、参数和返回值的规范。

## 2. 核心类

### 2.1 HighPrecisionOCR

主入口类，提供高精度OCR处理功能。

#### 构造函数
```python
def __init__(self, config: Optional[Dict[str, Any]] = None)
```

参数：
- config (dict, optional): 配置参数字典
  - pix2text_config (dict): Pix2Text配置参数
  - paddleocr_config (dict): Paddle OCR配置参数

#### 方法

##### process_single_image
处理单张图像

```python
def process_single_image(self, image_path: str, mode: str = 'combined') -> Dict[str, Any]
```

参数：
- image_path (str): 图像文件路径
- mode (str): 处理模式，可选值：'pix2text_only', 'paddleocr_only', 'combined'

返回值：
- dict: OCR处理结果
  - success (bool): 处理是否成功
  - image_path (str): 图像路径
  - result (dict): 识别结果（根据模式不同结构不同）
  - error (str, optional): 错误信息（仅在失败时存在）

##### process_batch_images
批量处理图像

```python
def process_batch_images(self, image_paths: List[str], mode: str = 'combined') -> List[Dict[str, Any]]
```

参数：
- image_paths (list): 图像文件路径列表
- mode (str): 处理模式，可选值：'pix2text_only', 'paddleocr_only', 'combined'

返回值：
- list: OCR处理结果列表，每个元素结构同process_single_image返回值

##### process_with_filtering
处理图像并过滤低置信度结果

```python
def process_with_filtering(self, image_paths: List[str], mode: str = 'combined', confidence_threshold: float = 0.8) -> Dict[str, Any]
```

参数：
- image_paths (list): 图像文件路径列表
- mode (str): 处理模式
- confidence_threshold (float): 置信度阈值

返回值：
- dict: 包含过滤结果的字典
  - all_results (list): 所有处理结果
  - high_confidence_results (list): 高置信度结果
  - filtered_count (int): 被过滤的结果数量
  - formulas (list): 提取的公式列表
  - texts (list): 提取的文本列表
  - success (bool): 处理是否成功

### 2.2 OCRProcessor

OCR组合处理器类，内部使用类。

#### 构造函数
```python
def __init__(self, pix2text_config: Optional[Dict[str, Any]] = None, paddleocr_config: Optional[Dict[str, Any]] = None)
```

参数：
- pix2text_config (dict, optional): Pix2Text配置参数
- paddleocr_config (dict, optional): Paddle OCR配置参数

#### 方法

##### process_image
处理单张图像

```python
def process_image(self, image_path: str, mode: OCRMode = OCRMode.COMBINED) -> Dict[str, Any]
```

参数：
- image_path (str): 图像文件路径
- mode (OCRMode): OCR处理模式枚举值

返回值：
- dict: OCR处理结果

##### batch_process
批量处理图像

```python
def batch_process(self, image_paths: list, mode: OCRMode = OCRMode.COMBINED) -> list
```

参数：
- image_paths (list): 图像文件路径列表
- mode (OCRMode): OCR处理模式枚举值

返回值：
- list: OCR处理结果列表

### 2.3 Pix2TextProcessor

Pix2Text处理器类，专门处理数学公式等专业符号。

#### 构造函数
```python
def __init__(self, config: Optional[Dict[str, Any]] = None)
```

参数：
- config (dict, optional): 配置参数字典
  - model_path (str, optional): 模型路径
  - device (str): 运行设备('cpu'或'cuda')
  - threshold (float): 置信度阈值

#### 方法

##### recognize_formula
识别数学公式

```python
def recognize_formula(self, image_path: str) -> Dict[str, Any]
```

参数：
- image_path (str): 图像文件路径

返回值：
- dict: 公式识别结果
  - latex (str): LaTeX格式的公式
  - confidence (float): 置信度
  - text (str): 文本格式的公式

##### recognize_text
识别普通文本

```python
def recognize_text(self, image_path: str) -> Dict[str, Any]
```

参数：
- image_path (str): 图像文件路径

返回值：
- dict: 文本识别结果
  - text (str): 识别的文本
  - confidence (float): 置信度

##### process_image
处理图像

```python
def process_image(self, image_path: str) -> Dict[str, Any]
```

参数：
- image_path (str): 图像文件路径

返回值：
- dict: 完整识别结果
  - formula (dict): 公式识别结果
  - text (dict): 文本识别结果
  - image_path (str): 图像路径

### 2.4 PaddleOCRProcessor

Paddle OCR处理器类，处理通用文本识别。

#### 构造函数
```python
def __init__(self, config: Optional[Dict[str, Any]] = None)
```

参数：
- config (dict, optional): 配置参数字典
  - lang (str): 语言设置('ch'中文, 'en'英文, 'mix'中英文混合)
  - det (bool): 是否启用文本检测
  - rec (bool): 是否启用文本识别
  - cls (bool): 是否启用方向分类
  - device (str): 运行设备('cpu'或'cuda')

#### 方法

##### recognize_text
识别图像中的文本

```python
def recognize_text(self, image_path: str) -> Dict[str, Any]
```

参数：
- image_path (str): 图像文件路径

返回值：
- dict: 文本识别结果
  - texts (list): 识别的文本列表
  - boxes (list): 文本框坐标
  - scores (list): 置信度分数

##### recognize_table
识别图像中的表格结构

```python
def recognize_table(self, image_path: str) -> Dict[str, Any]
```

参数：
- image_path (str): 图像文件路径

返回值：
- dict: 表格识别结果
  - table_structure (str): 表格结构描述
  - confidence (float): 置信度

##### process_image
处理图像

```python
def process_image(self, image_path: str) -> Dict[str, Any]
```

参数：
- image_path (str): 图像文件路径

返回值：
- dict: 完整识别结果
  - text_recognition (dict): 文本识别结果
  - table_recognition (dict, optional): 表格识别结果
  - image_path (str): 图像路径

## 3. 工具函数

### 3.1 combine_results
合并Pix2Text和Paddle OCR的识别结果

```python
def combine_results(pix2text_result: Dict[str, Any], paddleocr_result: Dict[str, Any]) -> Dict[str, Any]
```

参数：
- pix2text_result (dict): Pix2Text识别结果
- paddleocr_result (dict): Paddle OCR识别结果

返回值：
- dict: 合并后的结果字典

### 3.2 filter_high_confidence_results
过滤高置信度结果

```python
def filter_high_confidence_results(results: List[Dict[str, Any]], threshold: float = 0.8) -> List[Dict[str, Any]]
```

参数：
- results (list): OCR结果列表
- threshold (float): 置信度阈值

返回值：
- list: 过滤后的高置信度结果列表

### 3.3 extract_formulas
从结果中提取所有公式

```python
def extract_formulas(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]
```

参数：
- results (list): OCR结果列表

返回值：
- list: 公式列表

### 3.4 extract_texts
从结果中提取所有文本

```python
def extract_texts(results: List[Dict[str, Any]]) -> List[str]
```

参数：
- results (list): OCR结果列表

返回值：
- list: 文本列表

## 4. 枚举类型

### 4.1 OCRMode
OCR处理模式枚举

值：
- PIX2TEXT_ONLY: 仅使用Pix2Text
- PADDLE_OCR_ONLY: 仅使用Paddle OCR
- COMBINED: 组合使用两种OCR引擎

## 5. 配置参数详解

### 5.1 Pix2Text配置参数
- device (str): 运行设备，默认'cpu'
- threshold (float): 置信度阈值，默认0.9
- model_path (str, optional): 模型路径

### 5.2 Paddle OCR配置参数
- lang (str): 语言设置，默认'ch'
- det (bool): 是否启用文本检测，默认True
- rec (bool): 是否启用文本识别，默认True
- cls (bool): 是否启用方向分类，默认False
- device (str): 运行设备，默认'cpu'