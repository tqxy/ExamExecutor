#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
试卷 OCR 批量流程（issue #5 第 1-4 步）
PDF 转图片 -> 边缘检测分割题目边界 -> 逐题裁剪归档 -> 逐题 OCR 识别并归档 JSON
第 5 步（还原/归一化）见 question_restorer.py。

识别引擎沿用 src/main.py 的 OCRProcessor 接口。master 上该引擎返回占位值，
归档 JSON 原样保存引擎输出，不代表真实识别结果，详见 BATCH_WORKFLOW.md。
"""

import argparse
import json
import logging
import os
import re
import shutil
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import batch_paths

logger = logging.getLogger(__name__)

DEFAULT_DPI = 200
SCHEMA_VERSION = "1.0"
PAGE_IMAGES_DIR = batch_paths.PAGE_IMAGES_DIR
QUESTION_IMAGES_DIR = batch_paths.QUESTION_IMAGES_DIR
OCR_JSON_DIR = batch_paths.OCR_JSON_DIR
MANIFEST_FILE = batch_paths.MANIFEST_FILE
ERRORS_FILE = batch_paths.ERRORS_FILE

# 步骤名称，写入错误汇总便于定位问题环节
STEP_PDF_TO_IMAGE = "pdf_to_image"
STEP_DETECT_BOUNDARIES = "detect_boundaries"
STEP_CROP_QUESTION = "crop_question"
STEP_OCR = "ocr"
STEP_WRITE_ARCHIVE = "write_archive"


def now_iso() -> str:
    """当前时间的本地时区 ISO 字符串"""
    return datetime.now().astimezone().isoformat(timespec="seconds")


# 批量流程实际用到的 Python 依赖：模块名 -> 安装用的包名
REQUIRED_PACKAGES = (
    ("PyPDF2", "PyPDF2"),
    ("pdf2image", "pdf2image"),
    ("cv2", "opencv-python"),
    ("numpy", "numpy"),
    ("PIL", "Pillow"),
)


def missing_python_packages() -> List[str]:
    """返回未安装的依赖包名"""
    missing = []
    for module_name, package_name in REQUIRED_PACKAGES:
        try:
            __import__(module_name)
        except ImportError:
            missing.append(package_name)
    return missing


def check_dependencies() -> Optional[str]:
    """检查本流程实际依赖，返回可操作的错误信息；依赖齐全返回 None

    pdf2image 只是 poppler 命令行的包装，还要求系统侧存在 pdftoppm/pdfinfo。
    这里只检查并给出安装指引，不在运行时执行 pip install。

    Returns:
        str 或 None: 缺失依赖的可操作说明
    """
    missing = missing_python_packages()
    if missing:
        return "批量流程缺少 Python 依赖: {missing}。请执行: python -m pip install -r ocr_module/requirements.txt".format(
            missing=", ".join(missing)
        )

    if shutil.which("pdftoppm") is None or shutil.which("pdfinfo") is None:
        return (
            "pdf2image 需要系统侧的 poppler-utils（当前找不到 pdftoppm/pdfinfo）。"
            "请安装系统包，例如 Debian/Ubuntu: apt-get install poppler-utils；macOS: brew install poppler。"
        )

    return None


def extract_confidence(result: Any) -> Optional[float]:
    """从引擎返回中提取整体置信度

    Args:
        result: OCR 引擎返回的字典

    Returns:
        float 或 None: combined 模式取 confidence_score，
            单引擎模式退回 confidence 字段或最高的文本分数
    """
    if not isinstance(result, dict):
        return None

    for key in ("confidence_score", "confidence"):
        value = result.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)

    text_recognition = result.get("text_recognition")
    scores = text_recognition.get("scores") if isinstance(text_recognition, dict) else None
    if isinstance(scores, list):
        numeric = [float(score) for score in scores if isinstance(score, (int, float))]
        if numeric:
            return max(numeric)

    # 单引擎模式：pix2text_only 把置信度放在 formula / text 子结果里
    nested = [
        value.get("confidence")
        for value in (result.get("formula"), result.get("text"))
        if isinstance(value, dict) and isinstance(value.get("confidence"), (int, float))
    ]
    if nested:
        return float(max(nested))

    return None


def write_json(path: str, payload: Any) -> None:
    """写出 UTF-8 JSON，保留中文与正斜杠路径"""
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


class QuestionOCREngine:
    """逐题识别的封装，保持 src/main.py 的接口不变

    引擎按需惰性创建，调用方可以注入替身做离线测试。
    """

    def __init__(self, processor: Any = None, mode: str = "combined"):
        """
        Args:
            processor: OCR 处理器，默认使用 src.main.OCRProcessor
            mode: 处理模式，'pix2text_only' / 'paddleocr_only' / 'combined'
        """
        self.mode = mode
        self._processor = processor
        self._mode_enum = None

    @property
    def processor(self):
        if self._processor is None:
            from src.main import OCRProcessor

            self._processor = OCRProcessor()
        return self._processor

    @property
    def mode_enum(self):
        if self._mode_enum is None:
            from src.core.processor import OCRMode

            self._mode_enum = OCRMode(self.mode)
        return self._mode_enum

    def recognize(self, image_path: str) -> Dict[str, Any]:
        """识别单张题目图片

        Args:
            image_path: 题目图片路径

        Returns:
            dict: 引擎原样返回的结果

        Raises:
            Exception: 引擎异常原样上抛，由调用方逐条记录
        """
        result = self.processor.process_image(image_path, self.mode_enum)
        if not isinstance(result, dict):
            raise ValueError("OCR 引擎返回了非字典结果: {name}".format(name=type(result).__name__))
        return result


def build_ocr_document(
    *,
    engine: str,
    image_path: str,
    page_number: int,
    question_number: int,
    bounding_box: Optional[Sequence],
    ocr_result: Dict[str, Any],
    generated_at: str,
    source_pdf_path: str = "",
) -> Dict[str, Any]:
    """组装逐题 OCR 归档 JSON

    Args:
        engine: 引擎名称（处理模式）
        image_path: 题目图片的归档路径
        page_number: 来源页码
        question_number: 页内题号
        bounding_box: 页内坐标 [x, y, w, h]
        ocr_result: 引擎原样返回内容
        generated_at: 生成时间

    Returns:
        dict: 归档文档，ocr 字段原样保存引擎返回内容
    """
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at,
        "engine": engine,
        "placeholder_output": True,
        "note": "master 上 OCR 引擎返回占位值，本文件原样保存引擎输出，不用于断言识别文本正确性",
        "source": {
            "source_pdf_path": source_pdf_path,
            "question_image_path": image_path,
            "page_number": page_number,
            "question_number": question_number,
            "bounding_box": list(bounding_box) if bounding_box else None,
        },
        "confidence": extract_confidence(ocr_result),
        "ocr": ocr_result,
    }


def rasterize_pages(pdf_path: str, output_dir: str, dpi: int) -> Tuple[int, List[Tuple[int, str]]]:
    """第 1 步：PDF 转图片，逐页写出 page_{N}.png

    先用 PyPDF2 取页数，再逐页调用 pdf2image，这样页码与文件名的对应关系
    不受 pdf2image 临时文件命名规则的影响。

    Args:
        pdf_path: PDF 路径
        output_dir: 页面图片输出目录
        dpi: 转图分辨率

    Returns:
        tuple: (总页数, [(页码, 图片路径), ...])
    """
    import PyPDF2
    from pdf2image import convert_from_path

    with open(pdf_path, "rb") as handle:
        total_pages = len(PyPDF2.PdfReader(handle).pages)

    os.makedirs(output_dir, exist_ok=True)
    page_images: List[Tuple[int, str]] = []
    for number in range(1, total_pages + 1):
        images = convert_from_path(pdf_path, dpi=dpi, first_page=number, last_page=number)
        if not images:
            raise RuntimeError("第 {number} 页没有生成图像".format(number=number))
        target = os.path.join(output_dir, "page_{number}.png".format(number=number))
        images[0].save(target, "PNG")
        page_images.append((number, target))

    return total_pages, page_images


class ExamBatchPipeline:
    """一份或多份试卷的批量流程执行器

    单个环节失败只逐条记录错误，其余页面与题目继续处理。
    """

    def __init__(
        self,
        pdf_paths: List[str],
        run_dir: str,
        engine: Optional[QuestionOCREngine] = None,
        dpi: int = DEFAULT_DPI,
        generated_at: Optional[str] = None,
    ):
        """
        Args:
            pdf_paths: 试卷 PDF 路径列表
            run_dir: 本次运行的输出目录
            engine: 逐题识别引擎，默认真实引擎
            dpi: PDF 转图分辨率
            generated_at: 归档时间戳，默认当前时间

        Raises:
            ValueError: pdf_paths 为空
        """
        if not pdf_paths:
            raise ValueError("至少需要一份试卷 PDF")

        self.pdf_paths = [str(path) for path in pdf_paths]
        self.run_dir = os.path.abspath(run_dir)
        self.engine = engine if engine is not None else QuestionOCREngine()
        self.dpi = dpi
        self.generated_at = generated_at or now_iso()
        self.errors: List[Dict[str, Any]] = []
        self.documents: List[Dict[str, Any]] = []
        self.archive_roots = batch_paths.default_archive_roots(self.run_dir)
        self.pages_dir = os.path.join(self.run_dir, PAGE_IMAGES_DIR)
        self.questions_dir = os.path.join(self.run_dir, QUESTION_IMAGES_DIR)
        self.ocr_dir = os.path.join(self.run_dir, OCR_JSON_DIR)
        # 多份试卷时文件名加文档前缀，避免不同试卷的同页同名互相覆盖
        self.multiple_documents = len(self.pdf_paths) > 1

    def record_error(self, step: str, message: str, pdf: str = "",
                     page: Optional[int] = None, question: Optional[int] = None) -> Dict[str, Any]:
        """记录一条错误并继续处理"""
        entry = {
            "step": step,
            "pdf": batch_paths.to_archive_path(pdf, self.archive_roots) if pdf else "",
            "page": page,
            "question": question,
            "message": message,
        }
        self.errors.append(entry)
        logger.error("[%s] page=%s question=%s %s", step, page, question, message)
        return entry

    def page_image_name(self, document_index: int, page_number: int) -> str:
        """页面图片文件名"""
        prefix = "doc{index}_".format(index=document_index) if self.multiple_documents else ""
        return "{prefix}page_{page}.png".format(prefix=prefix, page=page_number)

    def question_image_name(self, document_index: int, page_number: int, question_number: int) -> str:
        """题目图片文件名，沿用 extracted_questions/page_{N}_question_{M}.png 命名"""
        prefix = "doc{index}_".format(index=document_index) if self.multiple_documents else ""
        return "{prefix}page_{page}_question_{question}.png".format(
            prefix=prefix, page=page_number, question=question_number
        )

    def ocr_json_name(self, document_index: int, page_number: int, question_number: int) -> str:
        """逐题 OCR JSON 文件名"""
        prefix = "doc{index}_".format(index=document_index) if self.multiple_documents else ""
        return "{prefix}page_{page}_question_{question}.json".format(
            prefix=prefix, page=page_number, question=question_number
        )

    def prepare(self) -> None:
        """创建输出目录，并清理上一轮运行留下的产物"""
        os.makedirs(self.run_dir, exist_ok=True)
        self._prune_previous_outputs()
        for directory in (self.pages_dir, self.questions_dir, self.ocr_dir):
            os.makedirs(directory, exist_ok=True)

    def _prune_previous_outputs(self) -> None:
        """重复运行时删除上一轮产物，保证同名文件被覆盖且不残留多余文件

        只清理本流程管理的目录与文件名，避免误删用户放进同一目录的其他内容。
        """
        if not os.path.exists(os.path.join(self.run_dir, MANIFEST_FILE)):
            return

        plans = (
            (self.pages_dir, re.compile(r"^(doc\d+_)?page_\d+\.png$")),
            (self.questions_dir, re.compile(r"^(doc\d+_)?page_\d+_question_\d+\.png$")),
            (self.ocr_dir, re.compile(r"^(doc\d+_)?page_\d+_question_\d+\.json$")),
        )
        for directory, pattern in plans:
            if not os.path.isdir(directory):
                continue
            for name in os.listdir(directory):
                if pattern.match(name):
                    os.remove(os.path.join(directory, name))

        for name in (ERRORS_FILE, batch_paths.RESTORED_FILE):
            path = os.path.join(self.run_dir, name)
            if os.path.exists(path):
                os.remove(path)

    def process_document(self, pdf_path: str, document_index: int) -> Dict[str, Any]:
        """处理一份试卷

        Args:
            pdf_path: 试卷 PDF 路径
            document_index: 试卷序号（1 起），用于多份试卷的文件名前缀

        Returns:
            dict: 该份试卷的归档索引
        """
        summary: Dict[str, Any] = {
            "source_pdf_path": batch_paths.to_archive_path(pdf_path, self.archive_roots),
            "total_pages": 0,
            "converted_pages": 0,
            "total_questions": 0,
            "pages": [],
        }

        if not os.path.isfile(pdf_path):
            self.record_error(STEP_PDF_TO_IMAGE, "试卷文件不存在: {path}".format(path=pdf_path), pdf=pdf_path)
            return summary

        try:
            total_pages, page_images = rasterize_pages(pdf_path, self.pages_dir, self.dpi)
        except Exception as error:
            self.record_error(STEP_PDF_TO_IMAGE, "PDF 转图片失败: {error}".format(error=error), pdf=pdf_path)
            return summary

        summary["total_pages"] = total_pages
        # 边界检测与裁剪依赖 OpenCV，按需导入，让本模块可以在轻量门禁下被引用
        from pdf_analyzer import PDFAnalyzer

        analyzer = PDFAnalyzer(pdf_path)

        for page_number, generated_path in page_images:
            page_path = os.path.join(self.pages_dir, self.page_image_name(document_index, page_number))
            try:
                if os.path.abspath(page_path) != os.path.abspath(generated_path):
                    os.replace(generated_path, page_path)
            except OSError as error:
                self.record_error(STEP_PDF_TO_IMAGE,
                                  "页面图片归档失败: {error}".format(error=error),
                                  pdf=pdf_path, page=page_number)
                continue

            summary["converted_pages"] += 1
            page_info: Dict[str, Any] = {
                "page_number": page_number,
                "page_image_path": batch_paths.to_archive_path(page_path, (self.run_dir,)),
                "question_count": 0,
                "questions": [],
            }
            summary["pages"].append(page_info)

            try:
                question_boxes = analyzer.detect_question_boundaries(page_path)
            except Exception as error:
                self.record_error(STEP_DETECT_BOUNDARIES,
                                  "题目边界检测失败: {error}".format(error=error),
                                  pdf=pdf_path, page=page_number)
                continue

            if not question_boxes:
                self.record_error(STEP_DETECT_BOUNDARIES, "该页未检测到题目区域", pdf=pdf_path, page=page_number)
                continue

            try:
                cropped_paths = analyzer.extract_questions(page_path, question_boxes, page_number,
                                                            output_dir=self.questions_dir)
            except Exception as error:
                self.record_error(STEP_CROP_QUESTION,
                                  "题目裁剪失败: {error}".format(error=error),
                                  pdf=pdf_path, page=page_number)
                continue

            if not cropped_paths:
                self.record_error(STEP_CROP_QUESTION,
                                  "该页题目裁剪未生成图片", pdf=pdf_path, page=page_number)
                continue

            for index, cropped_path in enumerate(cropped_paths):
                question_number = index + 1
                question_path = os.path.join(
                    self.questions_dir, self.question_image_name(document_index, page_number, question_number)
                )
                try:
                    if os.path.abspath(question_path) != os.path.abspath(cropped_path):
                        os.replace(cropped_path, question_path)
                except OSError as error:
                    self.record_error(STEP_CROP_QUESTION,
                                      "题目图片归档失败: {error}".format(error=error),
                                      pdf=pdf_path, page=page_number, question=question_number)
                    continue

                archive_entry: Dict[str, Any] = {
                    "question_number": question_number,
                    "question_image_path": batch_paths.to_archive_path(question_path, (self.run_dir,)),
                    "bounding_box": list(question_boxes[index]) if index < len(question_boxes) else None,
                    "ocr_json_path": None,
                }
                page_info["questions"].append(archive_entry)
                summary["total_questions"] += 1

                self.recognize_question(pdf_path, page_number, question_number, question_path,
                                        archive_entry, document_index, summary["source_pdf_path"])

            page_info["question_count"] = len(page_info["questions"])

        return summary

    def recognize_question(self, pdf_path: str, page_number: int, question_number: int,
                           question_path: str, archive_entry: Dict[str, Any],
                           document_index: int, source_pdf_path: str = "") -> None:
        """第 4 步：逐题识别并归档 JSON

        识别或写盘报错只记录该题错误，ocr_json_path 保持为 None，其余题目继续。
        """
        try:
            ocr_result = self.engine.recognize(question_path)
        except Exception as error:
            self.record_error(STEP_OCR,
                              "OCR 识别失败: {error}".format(error=error),
                              pdf=pdf_path, page=page_number, question=question_number)
            return

        batch_paths.normalize_paths(ocr_result, (self.run_dir,))
        document = build_ocr_document(
            engine=self.engine.mode,
            image_path=archive_entry["question_image_path"],
            page_number=page_number,
            question_number=question_number,
            bounding_box=archive_entry["bounding_box"],
            ocr_result=ocr_result,
            generated_at=self.generated_at,
            source_pdf_path=source_pdf_path,
        )

        json_path = os.path.join(
            self.ocr_dir, self.ocr_json_name(document_index, page_number, question_number)
        )
        try:
            write_json(json_path, document)
        except OSError as error:
            self.record_error(STEP_WRITE_ARCHIVE,
                              "OCR 结果归档失败: {error}".format(error=error),
                              pdf=pdf_path, page=page_number, question=question_number)
            return

        archive_entry["ocr_json_path"] = batch_paths.to_archive_path(json_path, (self.run_dir,))

    def build_manifest(self) -> Dict[str, Any]:
        """组装本次运行的归档索引，路径字段与其余归档保持一致的写法"""
        return {
            "schema_version": SCHEMA_VERSION,
            "generated_at": self.generated_at,
            "run_dir": batch_paths.to_archive_path(self.run_dir, self.archive_roots),
            # 其余 *_path 字段都相对 run_dir，manifest_path 等直接写文件名
            "dpi": self.dpi,
            "engine": self.engine.mode,
            "placeholder_output": True,
            "output_dirs": {
                "page_images": PAGE_IMAGES_DIR,
                "question_images": QUESTION_IMAGES_DIR,
                "ocr_json": OCR_JSON_DIR,
            },
            "manifest_path": MANIFEST_FILE,
            "errors_path": ERRORS_FILE,
            "restored_path": batch_paths.RESTORED_FILE,
            "total_documents": len(self.pdf_paths),
            "total_pages": sum(document["converted_pages"] for document in self.documents),
            "total_questions": sum(document["total_questions"] for document in self.documents),
            "total_errors": len(self.errors),
            "success": not self.errors,
            "documents": self.documents,
        }

    def run(self) -> Dict[str, Any]:
        """执行完整批量流程

        Returns:
            dict: 写入 manifest.json 的运行汇总
        """
        self.prepare()

        for index, pdf_path in enumerate(self.pdf_paths, start=1):
            self.documents.append(self.process_document(pdf_path, index))

        manifest = self.build_manifest()
        write_json(os.path.join(self.run_dir, ERRORS_FILE), {"errors": self.errors})
        write_json(os.path.join(self.run_dir, MANIFEST_FILE), manifest)

        logger.info("批量流程完成: %d 页 / %d 题 / %d 条错误",
                    manifest["total_pages"], manifest["total_questions"], manifest["total_errors"])
        return manifest


def format_error_location(error: Dict[str, Any]) -> str:
    """把一条错误的位置拼成可读文本"""
    parts = [error.get("pdf") or ""]
    if error.get("page") is not None:
        parts.append("page={page}".format(page=error["page"]))
    if error.get("question") is not None:
        parts.append("question={question}".format(question=error["question"]))
    location = " ".join(part for part in parts if part)
    return location or "全局"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="试卷 OCR 批量流程：PDF 转图片 -> 分割题目边界 -> 逐题裁剪归档 -> 逐题识别归档 JSON"
    )
    parser.add_argument("pdfs", nargs="+", help="一个或多个试卷 PDF 路径")
    parser.add_argument("-o", "--output-dir", required=True, help="本次运行的输出目录（产物不提交进仓库）")
    parser.add_argument("--dpi", type=int, default=DEFAULT_DPI, help="PDF 转图分辨率，默认 200")
    parser.add_argument("--mode", default="combined",
                        choices=("pix2text_only", "paddleocr_only", "combined"),
                        help="OCR 处理模式，默认 combined")
    parser.add_argument("--clear", action="store_true", help="运行前删除整个输出目录")
    parser.add_argument("--log-level", default="INFO", help="日志级别，默认 INFO")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """命令行入口：存在失败项时以非零退出码返回并列出失败项"""
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, str(args.log_level).upper(), logging.INFO),
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    dependency_error = check_dependencies()
    if dependency_error:
        print("依赖检查未通过: {error}".format(error=dependency_error), file=sys.stderr)
        return 2

    run_dir = os.path.abspath(args.output_dir)
    if args.clear and os.path.isdir(run_dir):
        shutil.rmtree(run_dir)

    pipeline = ExamBatchPipeline(args.pdfs, run_dir,
                                 engine=QuestionOCREngine(mode=args.mode), dpi=args.dpi)
    manifest = pipeline.run()

    print("批量流程完成: {pages} 页 / {questions} 题 / {errors} 条错误，输出目录: {run_dir}".format(
        pages=manifest["total_pages"],
        questions=manifest["total_questions"],
        errors=manifest["total_errors"],
        run_dir=run_dir,
    ))
    print("下一步可执行: python ocr_module/question_restorer.py {run_dir}".format(run_dir=run_dir))

    if pipeline.errors:
        print("失败项（详见 {path}）:".format(path=os.path.join(run_dir, ERRORS_FILE)), file=sys.stderr)
        for error in pipeline.errors:
            print("  - [{step}] {location}: {message}".format(
                step=error["step"], location=format_error_location(error), message=error["message"]
            ), file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
