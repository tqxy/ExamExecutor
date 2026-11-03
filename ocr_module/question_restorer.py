#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
题目还原模块（issue #5 第 5 步）
读取批量流程归档的逐题 OCR JSON，按 doc/题库自动化处理系统实施方案.md 的“结构化存储”
口径归一化为题目记录：题干、选项、答案、来源页、bounding_box、置信度。

不做版面渲染，也不做人工复核工作流。逐条错误记录后继续，不中断整批。
"""

import argparse
import json
import logging
import os
import re
import sys
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import batch_paths

logger = logging.getLogger(__name__)

SCHEMA_VERSION = "1.0"
RESTORED_FILE = batch_paths.RESTORED_FILE
STEP_RESTORE = "restore"

OPTION_PATTERN = re.compile(r"^\s*([A-Za-z])\s*[\.、．)）]\s*(.*)$")
# 行首锚定，且裸词「答案」必须带分隔符：避免「下列答案为无穷小量的个数」这类题干被误判成答案行
ANSWER_PATTERN = re.compile(r"^\s*(?:【\s*答案\s*】\s*[:：]?|答案\s*[:：])\s*(\S.*)$")


def now_iso() -> str:
    """当前时间的本地时区 ISO 字符串"""
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _read_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def collect_text_lines(document: Dict[str, Any]) -> List[str]:
    """从归档文档里取出识别文本行

    优先使用逐行文本（Paddle 的 texts 列表），退回 combined_text / text 字段按行切分。

    Args:
        document: 逐题 OCR 归档 JSON 解析后的字典

    Returns:
        list: 去掉空白的文本行列表
    """
    ocr = document.get("ocr") if isinstance(document.get("ocr"), dict) else {}
    lines: List[str] = []

    paddle_result = ocr.get("paddleocr_result") if isinstance(ocr.get("paddleocr_result"), dict) else {}
    text_recognition = (
        paddle_result.get("text_recognition") if isinstance(paddle_result.get("text_recognition"), dict) else {}
    )
    texts = text_recognition.get("texts")
    if isinstance(texts, list):
        lines.extend(str(text) for text in texts if str(text).strip())

    if not lines:
        candidates = []
        combined_text = ocr.get("combined_text")
        if isinstance(combined_text, str):
            candidates.append(combined_text)
        nested_text = ocr.get("text")
        if isinstance(nested_text, dict):
            nested_text = nested_text.get("text")
        if isinstance(nested_text, str):
            candidates.append(nested_text)
        for candidate in candidates:
            lines.extend(line.strip() for line in candidate.splitlines() if line.strip())

    return lines


def split_stem_and_options(lines: List[str]) -> Dict[str, Any]:
    """把文本行拆成题干、选项与答案

    三类行的判定相互独立，不依赖出现顺序：答案行不会关掉选项分支，
    选项也不会因为答案先出现而被拼进题干。出现多行答案时取第一行。

    Args:
        lines: 识别文本行

    Returns:
        dict: {"stem": str, "options": list, "answer": str | None}
    """
    stem_lines: List[str] = []
    options: List[Dict[str, str]] = []
    answers: List[str] = []

    for line in lines:
        answer_match = ANSWER_PATTERN.match(line)
        if answer_match:
            answers.append(answer_match.group(1).strip())
            continue

        option_match = OPTION_PATTERN.match(line)
        if option_match:
            options.append({"label": option_match.group(1).upper(), "text": option_match.group(2).strip()})
            continue

        stem_lines.append(line)

    return {
        "stem": "\n".join(stem_lines),
        "options": options,
        "answer": answers[0] if answers else None,
    }


def normalize_document(document: Dict[str, Any], *, ocr_json_path: str = "",
                       source_pdf_path: str = "") -> Dict[str, Any]:
    """把一份逐题 OCR 归档 JSON 归一化为结构化题目记录

    Args:
        document: 归档 JSON 解析后的字典
        ocr_json_path: 该 JSON 的归档路径，便于题源追溯
        source_pdf_path: 来源试卷的归档路径

    Returns:
        dict: 结构化题目记录
    """
    source = document.get("source") if isinstance(document.get("source"), dict) else {}
    bounding_box = source.get("bounding_box")
    page_number = source.get("page_number")
    question_number = source.get("question_number")

    parts = split_stem_and_options(collect_text_lines(document))
    question_id = os.path.splitext(os.path.basename(ocr_json_path))[0] if ocr_json_path else ""

    return {
        "question_id": question_id,
        "source_pdf_path": source_pdf_path or str(source.get("source_pdf_path", "")),
        "page_number": page_number,
        "question_number": question_number,
        "question_image_path": source.get("question_image_path", ""),
        "ocr_json_path": ocr_json_path,
        "engine": document.get("engine", ""),
        "stem": parts["stem"],
        "options": parts["options"],
        "answer": parts["answer"],
        "bounding_box": list(bounding_box) if isinstance(bounding_box, (list, tuple)) else None,
        "confidence": document.get("confidence"),
    }


class QuestionRestorer:
    """批量读取逐题 OCR JSON 并输出结构化题目记录"""

    def __init__(self, roots: Iterable[str] = (), generated_at: Optional[str] = None):
        """
        Args:
            roots: 解析归档相对路径时依次尝试的基准目录
            generated_at: 归档时间戳，默认当前时间
        """
        self.roots = tuple(roots) if roots else (os.getcwd(),)
        self.generated_at = generated_at or now_iso()
        self.records: List[Dict[str, Any]] = []
        self.errors: List[Dict[str, Any]] = []

    def record_error(self, message: str, ocr_json_path: str = "",
                     source_pdf_path: str = "") -> Dict[str, Any]:
        """记录一条还原错误并继续"""
        entry = {"step": STEP_RESTORE, "pdf": source_pdf_path, "ocr_json_path": ocr_json_path, "message": message}
        self.errors.append(entry)
        logger.error("[restore] %s: %s", ocr_json_path or "-", message)
        return entry

    def restore_file(self, ocr_json_path: str, *, source_pdf_path: str = "",
                     page_number: Optional[int] = None,
                     question_number: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """还原单个逐题 OCR JSON

        Args:
            ocr_json_path: 逐题 OCR JSON 路径（绝对路径或归档相对路径）
            source_pdf_path: 来源试卷归档路径
            page_number: 归档索引里的页码，用于补齐 JSON 缺失字段
            question_number: 归档索引里的题号，用于补齐 JSON 缺失字段

        Returns:
            dict 或 None：无法读取、缺少必要字段或内容为空的题目返回 None
        """
        resolved = batch_paths.resolve_archive_path(ocr_json_path, self.roots)

        try:
            document = _read_json(resolved)
        except (OSError, ValueError) as error:
            self.record_error(f"OCR JSON 无法读取或解析: {error}", ocr_json_path, source_pdf_path)
            return None

        if not isinstance(document, dict):
            self.record_error(f"OCR JSON 顶层不是对象: {type(document).__name__}", ocr_json_path, source_pdf_path)
            return None

        missing = [key for key in ("ocr", "source") if not isinstance(document.get(key), dict)]
        if missing:
            self.record_error(
                "OCR JSON 缺少必要字段: {fields}，已跳过".format(fields=", ".join(missing)),
                ocr_json_path, source_pdf_path,
            )
            return None

        archive_path = batch_paths.to_archive_path(resolved, self.roots)
        record = normalize_document(document, ocr_json_path=archive_path, source_pdf_path=source_pdf_path)

        source = document.get("source") if isinstance(document.get("source"), dict) else {}
        if record["page_number"] is None:
            record["page_number"] = page_number
        if record["question_number"] is None:
            record["question_number"] = question_number
        if not record["source_pdf_path"]:
            record["source_pdf_path"] = batch_paths.to_archive_path(
                source.get("source_pdf_path", ""), self.roots
            ) if source.get("source_pdf_path") else ""

        if not record["stem"] and not record["options"]:
            self.record_error("题目内容为空，已跳过", ocr_json_path, record["source_pdf_path"])
            return None

        self.records.append(record)
        return record

    def restore_documents(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """还原批量流程索引出的全部题目

        Args:
            documents: manifest 中的 documents 列表

        Returns:
            dict: 还原结果汇总
        """
        for document in documents:
            source_pdf_path = document.get("source_pdf_path", "")
            for page in document.get("pages", []):
                page_number = page.get("page_number")
                for question in page.get("questions", []):
                    ocr_json_path = question.get("ocr_json_path")
                    if not ocr_json_path:
                        self.record_error(
                            "该题没有归档 OCR JSON（识别或归档失败）",
                            "", source_pdf_path,
                        )
                        continue
                    self.restore_file(
                        ocr_json_path,
                        source_pdf_path=source_pdf_path,
                        page_number=page_number,
                        question_number=question.get("question_number"),
                    )

        return self.summary()

    def summary(self) -> Dict[str, Any]:
        """当前还原结果汇总"""
        return {
            "schema_version": SCHEMA_VERSION,
            "generated_at": self.generated_at,
            "total_questions": len(self.records),
            "total_errors": len(self.errors),
            "questions": self.records,
            "errors": self.errors,
        }


def collect_documents(run_dir: str) -> List[Dict[str, Any]]:
    """从运行目录的 manifest.json 读出题目索引；没有 manifest 时按目录扫描

    Args:
        run_dir: 批量流程运行目录

    Returns:
        list: 结构等同于 manifest.documents 的索引
    """
    manifest_path = os.path.join(run_dir, batch_paths.MANIFEST_FILE)
    if os.path.isfile(manifest_path):
        manifest = _read_json(manifest_path)
        documents = manifest.get("documents")
        if isinstance(documents, list):
            return documents

    pages_dir = os.path.join(run_dir, batch_paths.OCR_JSON_DIR)
    if not os.path.isdir(pages_dir):
        raise FileNotFoundError(
            f"{run_dir} 下既没有 manifest.json 也没有 {batch_paths.OCR_JSON_DIR}/ 目录，"
            "请先运行 python ocr_module/batch_process.py"
        )

    documents = [{"source_pdf_path": "", "pages": []}]
    page_pattern = re.compile(r"^(?P<prefix>doc\d+_)?page_(?P<page>\d+)_question_(?P<question>\d+)\.json$")
    for name in sorted(os.listdir(pages_dir)):
        match = page_pattern.match(name)
        if not match:
            continue
        pages = documents[0]["pages"]
        page_number = int(match.group("page"))
        page_info = next((item for item in pages if item["page_number"] == page_number), None)
        if page_info is None:
            page_info = {"page_number": page_number, "questions": []}
            pages.append(page_info)
        page_info["questions"].append({
            "question_number": int(match.group("question")),
            "ocr_json_path": os.path.join(pages_dir, name),
        })

    return documents


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="把逐题 OCR JSON 归一化为结构化题目记录")
    parser.add_argument("run_dir", help="批量流程运行目录（含 manifest.json 与 ocr_json/）")
    parser.add_argument("-o", "--output", default=None,
                        help=f"输出文件路径，默认写入运行目录下的 {RESTORED_FILE}")
    parser.add_argument("--log-level", default="INFO", help="日志级别，默认 INFO")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """命令行入口：存在还原错误时以非零退出码返回并列出失败项"""
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=getattr(logging, str(args.log_level).upper(), logging.INFO),
                        format="%(asctime)s - %(levelname)s - %(message)s")

    run_dir = os.path.abspath(args.run_dir)
    try:
        documents = collect_documents(run_dir)
    except (OSError, ValueError) as error:
        print(f"读取归档失败: {error}", file=sys.stderr)
        return 2

    restorer = QuestionRestorer(roots=(run_dir, batch_paths.repo_root(), os.getcwd()))
    result = restorer.restore_documents(documents)

    output_path = args.output or os.path.join(run_dir, RESTORED_FILE)
    os.makedirs(os.path.dirname(os.path.abspath(output_path)) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    print(f"还原完成: {result['total_questions']} 条题目记录 / {result['total_errors']} 条错误，输出: {output_path}")
    if restorer.errors:
        for error in restorer.errors:
            print(f"  - {error['ocr_json_path'] or error['pdf'] or '-'}: {error['message']}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
