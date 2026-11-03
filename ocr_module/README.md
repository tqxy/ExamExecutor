# 高精度OCR处理模块

本模块实现了基于Pix2Text和Paddle OCR组合方案的高精度OCR处理系统，专门用于处理试卷等教育场景中的复杂文档，支持数学公式、化学方程式等专业符号的高精度识别。

## 功能特点

1. **双引擎组合**：集成Pix2Text和Paddle OCR，发挥各自优势
2. **专业符号识别**：专门优化数学公式、化学方程式等专业符号识别
3. **高准确率**：整体识别准确率可达98.5%以上
4. **灵活配置**：支持多种处理模式和参数配置
5. **批量处理**：支持批量图像处理，提高处理效率

## 技术架构

- **Pix2Text处理器**：专门处理数学公式、化学方程式等专业符号
- **Paddle OCR处理器**：处理通用文本识别，结合Bi-LSTM-CRF模型提升准确性
- **结果合并器**：智能合并两种OCR引擎的结果，提高整体准确率
- **主控制器**：统一管理OCR处理流程，提供简洁的API接口

## 安装依赖

```bash
pip install -r requirements.txt
```

批量流程还需要系统侧的 poppler-utils（`pdf2image` 是其命令行包装）：

```bash
# Debian/Ubuntu
apt-get install poppler-utils
# macOS
brew install poppler
```

注意：Pix2Text可能需要从GitHub源码安装最新版本。

## 使用方法

### 基本使用

```python
from src.main import HighPrecisionOCR

# 配置参数
config = {
    'pix2text_config': {
        'device': 'cpu',
        'threshold': 0.9
    },
    'paddleocr_config': {
        'lang': 'ch',
        'device': 'cpu'
    }
}

# 创建OCR处理器
ocr = HighPrecisionOCR(config)

# 处理单张图像
result = ocr.process_single_image("example.png", "combined")
print(result)
```

### 批量处理

```python
# 批量处理图像
image_paths = ["image1.png", "image2.png", "image3.png"]
results = ocr.process_batch_images(image_paths, "combined")
```

### 带过滤的处理

```python
# 处理并过滤低置信度结果
filtered_results = ocr.process_with_filtering(
    image_paths, 
    mode="combined", 
    confidence_threshold=0.8
)
```

## 批量流程（issue #5 第 1-5 步）

从试卷 PDF 到结构化题目记录的批量流水线，详细字段定义与验收口径见 `BATCH_WORKFLOW.md`。

```bash
# 系统侧依赖：poppler-utils（提供 pdftoppm / pdfinfo）
python -m pip install -r requirements.txt

# 第 1-4 步：PDF 转图片 -> 分割题目边界 -> 逐题裁剪归档 -> 逐题识别归档 JSON
python batch_process.py "target/2023年考研数学（一）真题.pdf" -o /tmp/exam_run

# 第 5 步：把逐题 OCR JSON 归一化为结构化题目记录
python question_restorer.py /tmp/exam_run
```

运行目录结构（产物不提交进仓库，可整体删除完成清理）：

```text
/tmp/exam_run/
├── manifest.json              本次运行的归档索引
├── errors.json                逐条错误汇总
├── restored_questions.json    结构化题目记录
├── page_images/               page_{N}.png
├── question_images/           page_{N}_question_{M}.png
└── ocr_json/                  page_{N}_question_{M}.json
```

注意事项：

1. 输入 PDF 路径由操作者在运行时提供，多份试卷一次传入，产物文件名自动加 `doc{序号}_` 前缀。
2. 单个环节失败（某页无法转图、某页未检测到题目、某张识别报错）逐条写入 `errors.json`，其余页面与题目继续处理；
   流程结束时以非零退出码返回并在 stderr 列出失败项。
3. **当前 master 上的 Pix2Text / Paddle OCR 处理器返回占位值**（`_initialize_model` 只写日志，
   `recognize_*` 返回硬编码内容）。归档 JSON 原样保存引擎返回、`confidence` 与 `engine`，
   并带 `placeholder_output: true`，不代表真实识别结果。接入真实模型属于 issue #2，
   本流程只验收流水线与归档结构，不断言识别文本正确性。
4. 通用 API 化不在本流程范围内，按 issue 约定另立 issue。

## 处理模式

1. **pix2text_only**：仅使用Pix2Text处理
2. **paddleocr_only**：仅使用Paddle OCR处理
3. **combined**：组合使用两种OCR引擎（默认）

## 配置参数

### Pix2Text配置
- `device`: 运行设备 ('cpu' 或 'cuda')
- `threshold`: 置信度阈值
- `model_path`: 模型路径（可选）

### Paddle OCR配置
- `lang`: 语言设置 ('ch'中文, 'en'英文, 'mix'中英文混合)
- `det`: 是否启用文本检测
- `rec`: 是否启用文本识别
- `cls`: 是否启用方向分类
- `device`: 运行设备 ('cpu' 或 'cuda')

## 性能指标

> 以下是 `doc/题库自动化处理系统实施方案.md` 的目标值，当前 master 的 OCR 处理器返回占位值，
> 尚未接入真实模型，这些指标不代表本仓库的实测结果（见上文“批量流程”注意事项）。

- 整体识别准确率：≥98.5%
- 数学公式识别准确率：≥98%
- 化学方程式识别准确率：≥98%
- 版面分析准确率：≥95%
- 单张试卷处理时间：≤30秒
- 并发处理能力：≥100张/小时

## 目录结构

```
ocr_module/
├── requirements.txt          # 依赖包列表
├── batch_process.py          # 批量流程入口（第 1-4 步）
├── question_restorer.py      # 题目还原模块（第 5 步）
├── batch_paths.py            # 归档路径与运行目录布局
├── BATCH_WORKFLOW.md         # 批量流程与归档字段说明
├── test_batch_process.py     # 批量流程与还原模块自检
├── src/                     # 源代码目录
│   ├── __init__.py          # 包初始化文件
│   ├── main.py              # 主入口文件
│   ├── core/                # 核心处理模块
│   │   ├── __init__.py
│   │   └── processor.py     # OCR组合处理器
│   ├── pix2text/            # Pix2Text处理模块
│   │   ├── __init__.py
│   │   └── processor.py     # Pix2Text处理器
│   ├── paddleocr/           # Paddle OCR处理模块
│   │   ├── __init__.py
│   │   └── processor.py     # Paddle OCR处理器
│   └── utils/               # 工具模块
│       ├── __init__.py
│       └── result_combiner.py  # 结果合并工具
```

## 开发指南

1. 安装依赖包
2. 根据实际需求调整配置参数
3. 使用提供的API接口进行OCR处理
4. 可根据具体场景优化结果合并策略

## 注意事项

1. 对于包含大量数学公式的文档，建议使用combined模式以获得最佳效果
2. GPU加速可显著提升处理速度，建议在支持CUDA的环境下使用
3. 处理超长公式时，Pix2Text可能需要分块处理以保证准确率