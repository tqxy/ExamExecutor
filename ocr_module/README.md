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