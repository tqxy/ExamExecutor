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

## 5. 批量流程接口（issue #5）

流程范围、运行目录布局与归档 JSON 字段定义见 `BATCH_WORKFLOW.md`；本节只列接口签名。

### 5.1 batch_process

##### check_dependencies

```python
def check_dependencies() -> Optional[str]
```

返回值：
- str 或 None: 缺失依赖时的可操作提示（点名包名或系统包），依赖齐全返回 None。流程不在运行时执行 pip install

##### rasterize_pages

```python
def rasterize_pages(pdf_path: str, output_dir: str, dpi: int) -> Tuple[int, List[Tuple[int, str]]]
```

参数：
- pdf_path (str): 试卷 PDF 路径
- output_dir (str): 页面图片输出目录
- dpi (int): 转图分辨率

返回值：
- tuple: (总页数, [(页码, page_{N}.png 路径), ...])

##### QuestionOCREngine

逐题识别的封装，保持 `OCRProcessor.process_image` 接口不变。

```python
def __init__(self, processor: Optional[Any] = None, mode: str = 'combined')
def recognize(self, image_path: str) -> Dict[str, Any]
```

参数：
- processor: OCR 处理器，默认惰性创建 `src.main.OCRProcessor`
- mode (str): 'pix2text_only' / 'paddleocr_only' / 'combined'

返回值：
- dict: 引擎返回内容原样，供归档使用；非字典结果抛出 ValueError

##### ExamBatchPipeline

```python
def __init__(self, pdf_paths: List[str], run_dir: str, engine: Optional[QuestionOCREngine] = None, dpi: int = 200, generated_at: Optional[str] = None)
def run(self) -> Dict[str, Any]
def process_document(self, pdf_path: str, document_index: int) -> Dict[str, Any]
def prepare(self) -> None
def record_error(self, step: str, message: str, pdf: str = '', page: Optional[int] = None, question: Optional[int] = None) -> Dict[str, Any]
def build_manifest(self) -> Dict[str, Any]
```

参数：
- pdf_paths (list): 一个或多个试卷 PDF 路径，为空时抛出 ValueError
- run_dir (str): 本次运行的输出目录，产物不提交进仓库
- engine (QuestionOCREngine, optional): 识别引擎，默认真实引擎
- dpi (int): 转图分辨率，默认 200
- generated_at (str, optional): 归档时间戳，默认当前时间
- step (str): 失败环节，'pdf_to_image' / 'detect_boundaries' / 'crop_question' / 'ocr' / 'write_archive'

返回值：
- dict: run() 返回写入 manifest.json 的运行汇总；process_document 返回单份试卷的索引
- 单页/单题失败只逐条记录到 self.errors 与 errors.json，其余继续处理

##### main

```python
def main(argv: Optional[List[str]] = None) -> int
```

命令行入口。退出码：0 全部成功，1 存在失败项（stderr 列出），2 依赖缺失。

### 5.2 question_restorer

##### QuestionRestorer

```python
def __init__(self, roots: Iterable[str] = (), generated_at: Optional[str] = None)
def restore_file(self, ocr_json_path: str, *, source_pdf_path: str = '', page_number: Optional[int] = None, question_number: Optional[int] = None) -> Optional[Dict[str, Any]]
def restore_documents(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]
def summary(self) -> Dict[str, Any]
def record_error(self, message: str, ocr_json_path: str = '', source_pdf_path: str = '') -> Dict[str, Any]
```

参数：
- roots (iterable): 解析归档相对路径时依次尝试的基准目录
- ocr_json_path (str): 逐题 OCR JSON 路径，绝对路径或归档相对路径
- documents (list): manifest 中的 documents 列表

返回值：
- dict 或 None: restore_file 返回单条结构化题目记录，内容为空时返回 None 并记录错误
- dict: restore_documents / summary 返回还原结果汇总，含 questions 与逐条 errors

缺字段、内容为空、JSON 无法解析都只记录该条错误并继续，不抛未捕获异常。

##### 辅助函数

```python
def collect_text_lines(document: Dict[str, Any]) -> List[str]
def split_stem_and_options(lines: List[str]) -> Dict[str, Any]
def normalize_document(document: Dict[str, Any], *, ocr_json_path: str = '', source_pdf_path: str = '') -> Dict[str, Any]
def collect_documents(run_dir: str) -> List[Dict[str, Any]]
```

- collect_text_lines: 取引擎返回的文本行，优先逐行 texts，退回 combined_text / text
- split_stem_and_options: 返回 {'stem': str, 'options': list, 'answer': str | None}
- normalize_document: 归档 JSON 转结构化题目记录（题干、选项、答案、来源页、bounding_box、置信度）
- collect_documents: 优先读 manifest.json，没有则按 ocr_json/ 目录扫描
- main: 命令行入口。退出码 0 全部成功，1 存在还原错误（stderr 列出），2 运行目录没有可读归档

### 5.3 batch_paths

```python
def repo_root() -> str
def default_archive_roots(run_dir: Optional[str] = None) -> Tuple[str, ...]
def to_archive_path(path: Any, roots: Iterable[str] = ()) -> str
def resolve_archive_path(path: str, roots: Iterable[str] = ()) -> str
def normalize_paths(payload: Any, roots: Iterable[str] = ()) -> Any
def join_parts(*parts: Any) -> str
```

归档 JSON 里路径字段的统一写法：一律正斜杠分隔，不输出平台相关的反斜杠。

- `to_archive_path(path, roots)` 按 `roots` 顺序返回第一个命中的相对路径，都不命中时返回绝对路径的正斜杠写法
- 试卷 PDF 路径按“仓库根目录 → 当前工作目录”取值；页面、题目与逐题 JSON 路径按运行目录取值
- `default_archive_roots(run_dir)` 给出仓库根目录优先的基准列表
- `normalize_paths(payload, roots)` 递归改写 dict/list 中形如 `xxx_path` 的字段，用于引擎返回内容

### 5.4 PDFAnalyzer 的兼容性

`pdf_analyzer.py` 的公开方法签名保持可用，只为 `extract_questions` 增加可选参数：

```python
def extract_questions(self, image_path, question_boxes, page_number=1, output_dir=None)
```

- output_dir (str, optional): 题目图片输出目录；不传时仍写当前目录下的 extracted_questions，行为与之前一致

批量流程以调用方身份复用 `detect_question_boundaries` 与 `extract_questions`，不修改其检测与裁剪逻辑。

## 6. 配置参数详解

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