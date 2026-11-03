#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量流程与还原模块自检

全部使用运行时生成的临时 fixture：不依赖系统 poppler、OCR 模型，也不依赖仓库内 PDF 的绝对路径。
需要 OpenCV / PyPDF2 / pdf2image 的用例在依赖缺失时自动跳过，默认轻量门禁不受影响。
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import batch_paths
import batch_process
import question_restorer


def make_page_image(path, width=900, height=1200):
    """生成一张带两个黑色矩形块的页面图片，供边缘检测使用（仅依赖 Pillow）"""
    from PIL import Image

    image = Image.new("L", (width, height), color=255)
    for (left, top, right, bottom) in ((60, 100, 520, 300), (60, 500, 700, 760)):
        image.paste(0, (left, top, right, bottom))
    image.convert("RGB").save(path, "PNG")


def write_stub_pdf(path):
    """写一个占位 PDF 文件，页面渲染在测试里被替身接管"""
    with open(path, "wb") as handle:
        handle.write(b"%PDF-1.4\n% stub\n%%EOF\n")


def write_real_pdf(path, page_count=2):
    """用 Pillow 生成真实的多页 PDF，供第 1 步读取页数"""
    from PIL import Image

    colors = ("white", "black", "red")
    pages = [Image.new("RGB", (60, 40), color=color) for color in colors[:page_count]]
    pages[0].save(path, save_all=True, append_images=pages[1:])


def load_analyzer():
    """按需加载依赖 OpenCV 的 PDFAnalyzer，缺依赖时跳过当前用例"""
    pytest.importorskip("cv2", reason="题目边界检测与裁剪需要 opencv-python")
    from pdf_analyzer import PDFAnalyzer

    return PDFAnalyzer


class StubEngine:
    """替代 QuestionOCREngine，返回可预测的引擎结果"""

    def __init__(self, mode="combined", fail_on=()):
        self.mode = mode
        self.fail_on = set(fail_on)
        self.calls = []

    def recognize(self, image_path):
        self.calls.append(image_path)
        if os.path.basename(image_path) in self.fail_on:
            raise RuntimeError("模拟识别失败")
        return {
            "pix2text_result": {
                "formula": {"latex": "x^2", "confidence": 0.9, "text": "x^2"},
                "text": {"text": "设函数 f(x) 连续", "confidence": 0.9},
            },
            "paddleocr_result": {
                "text_recognition": {
                    "texts": ["设函数 f(x) 连续", "A. 0", "B. 1", "答案：B"],
                    "boxes": [[[10, 20], [100, 20], [100, 50], [10, 50]]],
                    "scores": [0.95, 0.87, 0.92],
                },
                "table_recognition": None,
                "image_path": image_path,
            },
            "combined_text": "设函数 f(x) 连续 A. 0 B. 1 答案：B",
            "formulas": [],
            "confidence_score": 0.91,
            "image_path": image_path,
            "processing_mode": "combined",
        }


class NotADictProcessor:
    """返回非字典结果的引擎替身"""

    def process_image(self, image_path, mode):
        return "不是字典"


@pytest.fixture
def run_dir(tmp_path):
    return str(tmp_path / "run")


@pytest.fixture
def pdf(tmp_path):
    path = str(tmp_path / "试卷.pdf")
    write_stub_pdf(path)
    return path


@pytest.fixture
def stubbed_pipeline(monkeypatch, pdf):
    """把第 1 步（依赖 poppler）与第 2 步的检测结果换成替身，其余环节走真实代码"""
    PDFAnalyzer = load_analyzer()

    def fake_rasterize(pdf_path, output_dir, dpi):
        os.makedirs(output_dir, exist_ok=True)
        pages = []
        for number in (1, 2):
            target = os.path.join(output_dir, "page_{number}.png".format(number=number))
            make_page_image(target)
            pages.append((number, target))
        return 2, pages

    monkeypatch.setattr(batch_process, "rasterize_pages", fake_rasterize)
    monkeypatch.setattr(
        PDFAnalyzer,
        "detect_question_boundaries",
        lambda self, image_path: [(60, 100, 460, 200), (60, 500, 640, 260)],
    )
    return pdf


def read_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def list_files(root):
    """列出目录内全部文件的相对路径（正斜杠）"""
    names = set()
    for directory, _dirs, files in os.walk(root):
        for name in files:
            names.add(os.path.relpath(os.path.join(directory, name), root).replace(os.sep, "/"))
    return names


# ---------------------------------------------------------------------------
# 归档路径约定
# ---------------------------------------------------------------------------


def test_archive_paths_prefer_repo_relative(tmp_path):
    """仓库内路径写成仓库相对路径，仓库外相对运行目录，都不带反斜杠"""
    repo = batch_paths.repo_root()
    inside = os.path.join(repo, "ocr_module", "batch_paths.py")
    assert batch_paths.to_archive_path(inside, (repo,)) == "ocr_module/batch_paths.py"

    run = str(tmp_path / "run")
    os.makedirs(run)
    outside = os.path.join(run, "page_1.png")
    with open(outside, "w", encoding="utf-8") as handle:
        handle.write("x")
    relative = batch_paths.to_archive_path(outside, (repo, run))
    assert "\\" not in relative
    assert relative.endswith("page_1.png")
    assert not os.path.isabs(relative)
    assert batch_paths.resolve_archive_path(relative, (run, repo)) == outside
    assert batch_paths.to_archive_path(None, (repo,)) == ""
    assert batch_paths.to_archive_path("", (repo,)) == ""


def test_normalize_paths_rewrites_path_fields():
    """只改写 xxx_path 字段，其他字符串保持不变"""
    payload = {
        "image_path": "/a/b/c.png",
        "nested": {"ocr_json_path": "/a/b/d.json", "keep": "/a/b/e.txt"},
        "items": [{"question_image_path": "/a/b/f.png"}],
    }
    batch_paths.normalize_paths(payload, ("/a",))
    assert payload["image_path"] == "b/c.png"
    assert payload["nested"]["ocr_json_path"] == "b/d.json"
    assert payload["nested"]["keep"] == "/a/b/e.txt"
    assert payload["items"][0]["question_image_path"] == "b/f.png"


def test_join_parts_uses_forward_slash():
    assert batch_paths.join_parts("a/", "b", "c.json") == "a/b/c.json"
    assert batch_paths.join_parts("a", "", None) == "a"


# ---------------------------------------------------------------------------
# 依赖检查
# ---------------------------------------------------------------------------


def test_check_dependencies_names_missing_packages(monkeypatch):
    """依赖缺失时给出点名包名的可操作提示，且不在运行时执行 pip install"""
    monkeypatch.setattr(batch_process, "missing_python_packages", lambda: ["pdf2image", "opencv-python"])
    message = batch_process.check_dependencies()
    assert "pdf2image" in message
    assert "opencv-python" in message
    assert "requirements.txt" in message

    monkeypatch.setattr(batch_process, "missing_python_packages", lambda: [])
    monkeypatch.setattr(batch_process.shutil, "which", lambda name: None)
    message = batch_process.check_dependencies()
    assert "poppler" in message
    assert "pip install" not in message

    monkeypatch.setattr(batch_process.shutil, "which", lambda name: "/usr/bin/" + name)
    assert batch_process.check_dependencies() is None


# ---------------------------------------------------------------------------
# 置信度与归档文档
# ---------------------------------------------------------------------------


def test_extract_confidence_reads_engine_fields():
    """三种处理模式的引擎返回都能取到置信度"""
    assert batch_process.extract_confidence({"confidence_score": 0.42}) == 0.42
    assert batch_process.extract_confidence({"confidence": 0.7}) == 0.7
    assert batch_process.extract_confidence({"text_recognition": {"scores": [0.3, 0.8, 0.5]}}) == 0.8
    assert batch_process.extract_confidence(
        {"formula": {"confidence": 0.9}, "text": {"confidence": 0.94}}) == 0.94
    assert batch_process.extract_confidence({"ocr": "无"}) is None
    assert batch_process.extract_confidence("不是字典") is None
    assert batch_process.extract_confidence({"confidence": True}) is None


def test_build_ocr_document_keeps_engine_output_verbatim():
    ocr_result = {"combined_text": "题干", "confidence_score": 0.5, "nested": {"image_path": "/x/y.png"}}
    document = batch_process.build_ocr_document(
        engine="combined",
        image_path="question_images/page_1_question_1.png",
        page_number=1,
        question_number=1,
        bounding_box=(60, 100, 460, 200),
        ocr_result=ocr_result,
        generated_at="2026-11-03T00:00:00+00:00",
        source_pdf_path="ocr_module/target/试卷.pdf",
    )
    assert document["ocr"] == ocr_result
    assert document["engine"] == "combined"
    assert document["confidence"] == 0.5
    assert document["placeholder_output"] is True
    assert "占位值" in document["note"]
    assert document["source"]["bounding_box"] == [60, 100, 460, 200]
    assert document["source"]["source_pdf_path"] == "ocr_module/target/试卷.pdf"


def test_pipeline_requires_at_least_one_pdf(run_dir):
    with pytest.raises(ValueError):
        batch_process.ExamBatchPipeline([], run_dir, engine=StubEngine())


def test_missing_pdf_is_recorded(run_dir):
    """试卷文件不存在时记录错误而不是抛异常"""
    pipeline = batch_process.ExamBatchPipeline(["不存在/试卷.pdf"], run_dir, engine=StubEngine())
    manifest = pipeline.run()
    assert manifest["total_errors"] == 1
    assert pipeline.errors[0]["step"] == "pdf_to_image"
    assert manifest["documents"][0]["pages"] == []
    assert os.path.isfile(os.path.join(run_dir, batch_process.MANIFEST_FILE))


def test_engine_recognize_rejects_non_dict_result():
    engine = batch_process.QuestionOCREngine(processor=NotADictProcessor(), mode="combined")
    with pytest.raises(ValueError):
        engine.recognize("x.png")


def test_engine_keeps_main_interface_modes():
    """引擎封装沿用 src/main.py 的 OCRProcessor 接口与 OCRMode 取值"""
    from src.core.processor import OCRMode

    engine = batch_process.QuestionOCREngine(mode="paddleocr_only")
    assert engine.mode == "paddleocr_only"
    assert engine.mode_enum is OCRMode.PADDLE_OCR_ONLY
    assert batch_process.QuestionOCREngine().mode_enum is OCRMode.COMBINED
    assert engine.processor is engine.processor


# ---------------------------------------------------------------------------
# 第 1 步：PDF 转图片
# ---------------------------------------------------------------------------


def test_rasterize_pages_writes_one_file_per_page(monkeypatch, tmp_path):
    """按页码写出 page_{N}.png，页数来自 PyPDF2"""
    pdf2image = pytest.importorskip("pdf2image", reason="第 1 步需要 pdf2image")
    PyPDF2 = pytest.importorskip("PyPDF2", reason="第 1 步需要 PyPDF2")
    from PIL import Image

    pdf_path = str(tmp_path / "real.pdf")
    write_real_pdf(pdf_path, page_count=2)
    with open(pdf_path, "rb") as handle:
        assert len(PyPDF2.PdfReader(handle).pages) == 2

    captured = []

    def fake_convert(path, dpi=200, first_page=None, last_page=None, **kwargs):
        captured.append((first_page, last_page, dpi))
        return [Image.new("RGB", (60, 40), color="white")]

    monkeypatch.setattr(pdf2image, "convert_from_path", fake_convert)
    output_dir = str(tmp_path / "pages")
    total, images = batch_process.rasterize_pages(pdf_path, output_dir, 150)

    assert total == 2
    assert [name for _num, name in images] == [
        os.path.join(output_dir, "page_1.png"),
        os.path.join(output_dir, "page_2.png"),
    ]
    assert captured == [(1, 1, 150), (2, 2, 150)]
    for _num, name in images:
        assert os.path.isfile(name)


def test_rasterize_pages_raises_on_empty_page(monkeypatch, tmp_path):
    """某页转图失败时抛异常，由调用方逐条记录而不是中断整批"""
    pdf2image = pytest.importorskip("pdf2image", reason="第 1 步需要 pdf2image")
    pytest.importorskip("PyPDF2", reason="第 1 步需要 PyPDF2")

    pdf_path = str(tmp_path / "real.pdf")
    write_real_pdf(pdf_path, page_count=1)
    monkeypatch.setattr(pdf2image, "convert_from_path", lambda *args, **kwargs: [])
    with pytest.raises(RuntimeError):
        batch_process.rasterize_pages(pdf_path, str(tmp_path / "pages"), 100)


def test_unreadable_pdf_records_error_without_crash(tmp_path, run_dir):
    """无法解析的 PDF 记为一条 pdf_to_image 错误"""
    pytest.importorskip("PyPDF2", reason="第 1 步需要 PyPDF2")
    broken = str(tmp_path / "broken.pdf")
    write_stub_pdf(broken)
    pipeline = batch_process.ExamBatchPipeline([broken], run_dir, engine=StubEngine())
    manifest = pipeline.run()
    assert manifest["total_errors"] == 1
    assert pipeline.errors[0]["step"] == "pdf_to_image"


# ---------------------------------------------------------------------------
# 第 2-4 步：分割、裁剪、识别归档
# ---------------------------------------------------------------------------


def test_pipeline_archives_pages_questions_and_ocr_json(stubbed_pipeline, run_dir):
    """验收第 1-4 步的产物：页面图片、逐题图片、逐题 JSON 与归档索引"""
    pipeline = batch_process.ExamBatchPipeline([stubbed_pipeline], run_dir, engine=StubEngine())
    manifest = pipeline.run()

    assert manifest["total_pages"] == 2
    assert manifest["total_questions"] == 4
    assert manifest["total_errors"] == 0
    assert manifest["success"] is True
    assert pipeline.errors == []

    files = list_files(run_dir)
    for expected in (
        "page_images/page_1.png",
        "page_images/page_2.png",
        "question_images/page_1_question_1.png",
        "question_images/page_2_question_2.png",
        "ocr_json/page_1_question_1.json",
        "ocr_json/page_2_question_2.json",
        "manifest.json",
        "errors.json",
    ):
        assert expected in files

    document = read_json(os.path.join(run_dir, "ocr_json", "page_1_question_1.json"))
    assert document["engine"] == "combined"
    assert document["confidence"] == 0.91
    assert document["ocr"]["combined_text"] == "设函数 f(x) 连续 A. 0 B. 1 答案：B"
    assert document["source"]["page_number"] == 1
    assert document["source"]["question_number"] == 1
    assert document["source"]["bounding_box"] == [60, 100, 460, 200]
    assert document["source"]["source_pdf_path"].endswith(".pdf")


def test_archive_paths_are_forward_slash_and_relative(stubbed_pipeline, run_dir):
    """归档 JSON 使用正斜杠，运行目录内的产物相对 run_dir，输入 PDF 相对仓库"""
    batch_process.ExamBatchPipeline([stubbed_pipeline], run_dir, engine=StubEngine()).run()

    manifest = read_json(os.path.join(run_dir, "manifest.json"))
    page = manifest["documents"][0]["pages"][0]
    assert "\\" not in json.dumps(manifest, ensure_ascii=False)
    assert page["page_image_path"] == "page_images/page_1.png"
    assert page["questions"][0]["question_image_path"] == "question_images/page_1_question_1.png"
    assert page["questions"][0]["ocr_json_path"] == "ocr_json/page_1_question_1.json"
    assert manifest["manifest_path"] == "manifest.json"
    assert os.path.isfile(os.path.join(run_dir, page["page_image_path"]))
    # 输入 PDF 在仓库与运行目录之外，按文档约定退回绝对路径的正斜杠写法
    source_pdf_path = manifest["documents"][0]["source_pdf_path"]
    assert source_pdf_path == os.path.abspath(stubbed_pipeline).replace(os.sep, "/")
    assert "\\" not in source_pdf_path

    document = read_json(os.path.join(run_dir, "ocr_json", "page_1_question_1.json"))
    assert "\\" not in json.dumps(document, ensure_ascii=False)


def test_source_pdf_path_is_repo_relative_when_inside_repo(monkeypatch, tmp_path, run_dir):
    """输入 PDF 位于仓库内时，归档写成仓库相对路径（真实使用场景）"""
    PDFAnalyzer = load_analyzer()
    repo = tmp_path / "repo"
    target = repo / "target"
    target.mkdir(parents=True)
    pdf_path = str(target / "试卷.pdf")
    write_stub_pdf(pdf_path)
    monkeypatch.setattr(batch_paths, "repo_root", lambda: str(repo))

    def fake_rasterize(pdf_path_, output_dir, dpi):
        os.makedirs(output_dir, exist_ok=True)
        made = os.path.join(output_dir, "page_1.png")
        make_page_image(made)
        return 1, [(1, made)]

    monkeypatch.setattr(batch_process, "rasterize_pages", fake_rasterize)
    monkeypatch.setattr(PDFAnalyzer, "detect_question_boundaries",
                        lambda self, image_path: [(60, 100, 460, 200)])

    batch_process.ExamBatchPipeline([pdf_path], run_dir, engine=StubEngine()).run()
    manifest = read_json(os.path.join(run_dir, "manifest.json"))
    assert manifest["documents"][0]["source_pdf_path"] == "target/试卷.pdf"

    document = read_json(os.path.join(run_dir, "ocr_json", "page_1_question_1.json"))
    assert document["source"]["source_pdf_path"] == "target/试卷.pdf"


def test_engine_paths_inside_result_are_normalized(stubbed_pipeline, run_dir):
    """引擎返回里的 image_path 也统一写成相对运行目录的路径"""
    batch_process.ExamBatchPipeline([stubbed_pipeline], run_dir, engine=StubEngine()).run()
    document = read_json(os.path.join(run_dir, "ocr_json", "page_1_question_1.json"))
    assert document["ocr"]["image_path"] == "question_images/page_1_question_1.png"
    nested = document["ocr"]["paddleocr_result"]["image_path"]
    assert not os.path.isabs(nested)
    assert "\\" not in json.dumps(document["ocr"], ensure_ascii=False)


def test_rerun_produces_same_files_without_stale_leftovers(monkeypatch, pdf, run_dir):
    """重复运行生成同名文件，且不残留上一轮的多余文件"""

    def make_rasterizer(page_count):
        def fake_rasterize(pdf_path, output_dir, dpi):
            os.makedirs(output_dir, exist_ok=True)
            pages = []
            for number in range(1, page_count + 1):
                target = os.path.join(output_dir, "page_{number}.png".format(number=number))
                make_page_image(target)
                pages.append((number, target))
            return page_count, pages

        return fake_rasterize

    PDFAnalyzer = load_analyzer()
    monkeypatch.setattr(PDFAnalyzer, "detect_question_boundaries",
                        lambda self, image_path: [(60, 100, 460, 200)])
    monkeypatch.setattr(batch_process, "rasterize_pages", make_rasterizer(3))
    batch_process.ExamBatchPipeline([pdf], run_dir, engine=StubEngine()).run()
    assert "ocr_json/page_3_question_1.json" in list_files(run_dir)

    # 第二次运行输入变少，上一轮第 3 页的产物必须被清掉
    monkeypatch.setattr(batch_process, "rasterize_pages", make_rasterizer(2))
    manifest = batch_process.ExamBatchPipeline([pdf], run_dir, engine=StubEngine()).run()
    files = list_files(run_dir)
    assert "ocr_json/page_3_question_1.json" not in files
    assert "page_images/page_3.png" not in files
    assert "ocr_json/page_2_question_1.json" in files
    assert manifest["total_pages"] == 2


def test_rerun_same_input_keeps_identical_file_names(stubbed_pipeline, run_dir):
    """同一输入重复运行生成同名文件，不新增文件"""
    batch_process.ExamBatchPipeline([stubbed_pipeline], run_dir, engine=StubEngine()).run()
    first = list_files(run_dir)
    batch_process.ExamBatchPipeline([stubbed_pipeline], run_dir, engine=StubEngine()).run()
    assert list_files(run_dir) == first


def test_prune_only_touches_pipeline_outputs(run_dir):
    """清理只删除本流程管理的文件，不动用户放进同一目录的其他内容"""
    os.makedirs(os.path.join(run_dir, batch_process.PAGE_IMAGES_DIR), exist_ok=True)
    os.makedirs(os.path.join(run_dir, batch_process.OCR_JSON_DIR), exist_ok=True)
    for name in ("page_1.png", "page_9.png", "notes.txt"):
        with open(os.path.join(run_dir, batch_process.PAGE_IMAGES_DIR, name), "w", encoding="utf-8") as handle:
            handle.write("x")
    with open(os.path.join(run_dir, batch_process.OCR_JSON_DIR, "page_1_question_1.json"),
              "w", encoding="utf-8") as handle:
        handle.write("{}")
    with open(os.path.join(run_dir, batch_process.MANIFEST_FILE), "w", encoding="utf-8") as handle:
        handle.write("{}")

    batch_process.ExamBatchPipeline(["x.pdf"], run_dir, engine=StubEngine()).prepare()
    files = list_files(run_dir)
    assert "page_images/page_9.png" not in files
    assert "page_images/notes.txt" in files
    assert "ocr_json/page_1_question_1.json" not in files


def test_multiple_documents_get_distinct_prefixes(monkeypatch, tmp_path, run_dir):
    """多份试卷时同名页面不互相覆盖"""
    PDFAnalyzer = load_analyzer()
    paths = []
    for name in ("a.pdf", "b.pdf"):
        path = str(tmp_path / name)
        write_stub_pdf(path)
        paths.append(path)

    def fake_rasterize(pdf_path, output_dir, dpi):
        os.makedirs(output_dir, exist_ok=True)
        target = os.path.join(output_dir, "page_1.png")
        make_page_image(target)
        return 1, [(1, target)]

    monkeypatch.setattr(batch_process, "rasterize_pages", fake_rasterize)
    monkeypatch.setattr(PDFAnalyzer, "detect_question_boundaries",
                        lambda self, image_path: [(60, 100, 460, 200)])

    manifest = batch_process.ExamBatchPipeline(paths, run_dir, engine=StubEngine()).run()
    files = list_files(run_dir)
    assert manifest["total_pages"] == 2
    assert manifest["total_questions"] == 2
    assert "page_images/doc1_page_1.png" in files
    assert "page_images/doc2_page_1.png" in files
    assert "question_images/doc1_page_1_question_1.png" in files
    assert "ocr_json/doc2_page_1_question_1.json" in files


# ---------------------------------------------------------------------------
# 失败处理
# ---------------------------------------------------------------------------


def test_failures_are_recorded_per_item_and_others_continue(monkeypatch, pdf, run_dir):
    """某页未检测到题目、某题识别报错都逐条记录，其余题目继续"""
    PDFAnalyzer = load_analyzer()

    def fake_rasterize(pdf_path, output_dir, dpi):
        os.makedirs(output_dir, exist_ok=True)
        pages = []
        for number in (1, 2, 3):
            target = os.path.join(output_dir, "page_{number}.png".format(number=number))
            make_page_image(target)
            pages.append((number, target))
        return 3, pages

    def detect(self, image_path):
        if image_path.endswith("page_2.png"):
            return []
        return [(60, 100, 460, 200)]

    monkeypatch.setattr(batch_process, "rasterize_pages", fake_rasterize)
    monkeypatch.setattr(PDFAnalyzer, "detect_question_boundaries", detect)

    engine = StubEngine(fail_on=("page_3_question_1.png",))
    pipeline = batch_process.ExamBatchPipeline([pdf], run_dir, engine=engine)
    manifest = pipeline.run()

    assert sorted(error["step"] for error in pipeline.errors) == ["detect_boundaries", "ocr"]
    failing = [error for error in pipeline.errors if error["step"] == "detect_boundaries"][0]
    assert failing["page"] == 2
    assert failing["pdf"].endswith(".pdf")

    assert manifest["total_questions"] == 2
    assert manifest["total_errors"] == 2
    assert manifest["success"] is False

    files = list_files(run_dir)
    assert "ocr_json/page_1_question_1.json" in files
    assert "question_images/page_3_question_1.png" in files
    assert "ocr_json/page_3_question_1.json" not in files
    page3 = manifest["documents"][0]["pages"][2]
    assert page3["questions"][0]["ocr_json_path"] is None

    errors_file = read_json(os.path.join(run_dir, "errors.json"))
    assert len(errors_file["errors"]) == 2


def test_pdf_conversion_failure_keeps_other_documents(monkeypatch, tmp_path, run_dir):
    """某份试卷转图失败时，其余试卷继续处理"""
    PDFAnalyzer = load_analyzer()
    broken = str(tmp_path / "broken.pdf")
    working = str(tmp_path / "working.pdf")
    for path in (broken, working):
        write_stub_pdf(path)

    def fake_rasterize(pdf_path, output_dir, dpi):
        if pdf_path == broken:
            raise RuntimeError("模拟转换失败")
        os.makedirs(output_dir, exist_ok=True)
        target = os.path.join(output_dir, "page_1.png")
        make_page_image(target)
        return 1, [(1, target)]

    monkeypatch.setattr(batch_process, "rasterize_pages", fake_rasterize)
    monkeypatch.setattr(PDFAnalyzer, "detect_question_boundaries",
                        lambda self, image_path: [(60, 100, 460, 200)])

    pipeline = batch_process.ExamBatchPipeline([broken, working], run_dir, engine=StubEngine())
    manifest = pipeline.run()

    assert manifest["total_documents"] == 2
    assert manifest["total_questions"] == 1
    assert pipeline.errors[0]["step"] == "pdf_to_image"
    assert "page_images/doc2_page_1.png" in list_files(run_dir)


# ---------------------------------------------------------------------------
# 第 5 步：还原模块
# ---------------------------------------------------------------------------


def test_restorer_normalizes_archive_document():
    """归一化输出包含题干、选项、答案、来源页、bounding_box、置信度"""
    document = {
        "engine": "combined",
        "confidence": 0.83,
        "ocr": {"paddleocr_result": {"text_recognition": {
            "texts": ["求下列极限", "A. 1", "B. 2", "C. 3", "答案：C"]}}},
        "source": {
            "source_pdf_path": "ocr_module/target/试卷.pdf",
            "question_image_path": "question_images/page_2_question_3.png",
            "page_number": 2,
            "question_number": 3,
            "bounding_box": [10, 20, 30, 40],
        },
    }
    record = question_restorer.normalize_document(document, ocr_json_path="ocr_json/page_2_question_3.json")
    assert record["stem"] == "求下列极限"
    assert [option["label"] for option in record["options"]] == ["A", "B", "C"]
    assert record["options"][1]["text"] == "2"
    assert record["answer"] == "C"
    assert record["page_number"] == 2
    assert record["question_number"] == 3
    assert record["bounding_box"] == [10, 20, 30, 40]
    assert record["confidence"] == 0.83
    assert record["source_pdf_path"] == "ocr_module/target/试卷.pdf"
    assert record["question_id"] == "page_2_question_3"


def test_restorer_falls_back_to_combined_text():
    document = {"engine": "combined", "ocr": {"combined_text": "第一行\n第二行"}, "source": {}}
    record = question_restorer.normalize_document(document, ocr_json_path="page_1_question_1.json")
    assert record["stem"] == "第一行\n第二行"
    assert record["options"] == []
    assert record["answer"] is None


def test_restorer_builds_structured_records(stubbed_pipeline, run_dir):
    """第 5 步读取第 4 步归档的 JSON，产出结构化题目记录"""
    batch_process.ExamBatchPipeline([stubbed_pipeline], run_dir, engine=StubEngine()).run()

    manifest = read_json(os.path.join(run_dir, "manifest.json"))
    restorer = question_restorer.QuestionRestorer(roots=batch_paths.default_archive_roots(run_dir))
    result = restorer.restore_documents(manifest["documents"])

    assert result["total_errors"] == 0
    assert result["total_questions"] == 4
    record = result["questions"][0]
    for field in ("stem", "options", "answer", "page_number", "bounding_box", "confidence"):
        assert field in record
    assert record["stem"] == "设函数 f(x) 连续"
    assert [option["label"] for option in record["options"]] == ["A", "B"]
    assert record["answer"] == "B"
    assert record["page_number"] == 1
    assert record["question_number"] == 1
    assert record["question_image_path"] == "question_images/page_1_question_1.png"
    assert record["ocr_json_path"] == "ocr_json/page_1_question_1.json"
    assert record["bounding_box"] == [60, 100, 460, 200]
    assert record["confidence"] == 0.91
    assert "\\" not in json.dumps(result, ensure_ascii=False)


def test_restorer_records_errors_and_continues(tmp_path):
    """缺字段、内容为空、JSON 无法解析都记录错误并继续，不抛未捕获异常"""
    ocr_dir = tmp_path / "ocr_json"
    ocr_dir.mkdir()
    roots = (str(tmp_path),)

    (ocr_dir / "page_1_question_1.json").write_text("{ 这不是合法 JSON", encoding="utf-8")
    (ocr_dir / "page_1_question_2.json").write_text(
        json.dumps({"generated_at": "2026-11-03T00:00:00+00:00"}), encoding="utf-8")
    (ocr_dir / "page_2_question_1.json").write_text(
        json.dumps({"engine": "combined", "ocr": {"combined_text": "   "},
                    "source": {"page_number": 2, "question_number": 1}}),
        encoding="utf-8")
    (ocr_dir / "page_2_question_2.json").write_text(json.dumps([1, 2]), encoding="utf-8")
    (ocr_dir / "page_3_question_1.json").write_text(
        json.dumps({
            "engine": "combined",
            "confidence": 0.6,
            "ocr": {"paddleocr_result": {"text_recognition": {"texts": ["求极限", "答案：1"]}}},
            "source": {"page_number": 3, "question_number": 1,
                       "question_image_path": "a.png", "bounding_box": [1, 2, 3, 4]},
        }),
        encoding="utf-8")

    restorer = question_restorer.QuestionRestorer(roots=roots)
    for name in ("page_1_question_1.json", "page_1_question_2.json", "page_2_question_1.json",
                 "page_2_question_2.json", "missing.json", "page_3_question_1.json"):
        restorer.restore_file("ocr_json/{name}".format(name=name))

    result = restorer.summary()
    assert result["total_questions"] == 1
    assert result["questions"][0]["stem"] == "求极限"
    assert result["questions"][0]["answer"] == "1"
    messages = " ".join(error["message"] for error in result["errors"])
    assert "无法读取或解析" in messages
    assert "缺少必要字段" in messages
    assert "内容为空" in messages
    assert len(result["errors"]) == 6


def test_restorer_flags_questions_without_archive_json(tmp_path):
    """manifest 里 ocr_json_path 为空的题目记录错误但不中断"""
    documents = [{
        "source_pdf_path": "paper.pdf",
        "pages": [{"page_number": 1, "questions": [{"question_number": 1, "ocr_json_path": None}]}],
    }]
    restorer = question_restorer.QuestionRestorer(roots=(str(tmp_path),))
    result = restorer.restore_documents(documents)
    assert result["total_questions"] == 0
    assert result["total_errors"] == 1
    assert "没有归档 OCR JSON" in result["errors"][0]["message"]


def test_collect_documents_scans_ocr_dir_without_manifest(tmp_path):
    """没有 manifest 时按 ocr_json/ 目录扫描，仍可还原"""
    ocr_dir = tmp_path / "ocr_json"
    ocr_dir.mkdir()
    document = {
        "engine": "combined",
        "confidence": 0.5,
        "ocr": {"combined_text": "计算行列式"},
        "source": {"page_number": 1, "question_number": 1},
    }
    (ocr_dir / "page_1_question_1.json").write_text(json.dumps(document), encoding="utf-8")

    documents = question_restorer.collect_documents(str(tmp_path))
    assert documents[0]["pages"][0]["questions"][0]["question_number"] == 1

    restorer = question_restorer.QuestionRestorer(roots=(str(tmp_path),))
    result = restorer.restore_documents(documents)
    assert result["total_questions"] == 1
    assert result["questions"][0]["stem"] == "计算行列式"


def test_restorer_cli_writes_structured_records(stubbed_pipeline, run_dir):
    """命令行入口从运行目录读索引并写出结构化记录"""
    batch_process.ExamBatchPipeline([stubbed_pipeline], run_dir, engine=StubEngine()).run()

    exit_code = question_restorer.main([run_dir, "--log-level", "ERROR"])
    assert exit_code == 0
    output = read_json(os.path.join(run_dir, batch_paths.RESTORED_FILE))
    assert output["total_questions"] == 4
    assert "\\" not in json.dumps(output, ensure_ascii=False)


def test_restorer_missing_run_dir(tmp_path, capsys):
    """运行目录没有归档时给出可操作提示并以非零退出码返回"""
    assert question_restorer.main([str(tmp_path / "nope"), "--log-level", "ERROR"]) == 2
    assert "请先运行" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# 命令行入口
# ---------------------------------------------------------------------------


def test_batch_cli_exit_code_reports_failures(monkeypatch, pdf, run_dir, capsys):
    """流程结束时以非零退出码返回并指出失败项"""

    def raise_conversion_error(*args, **kwargs):
        raise RuntimeError("模拟 poppler 失败")

    monkeypatch.setattr(batch_process, "rasterize_pages", raise_conversion_error)
    monkeypatch.setattr(batch_process, "QuestionOCREngine", lambda mode="combined": StubEngine(mode=mode))
    monkeypatch.setattr(batch_process, "check_dependencies", lambda: None)

    exit_code = batch_process.main([pdf, "-o", run_dir, "--log-level", "ERROR"])
    assert exit_code == 1
    captured = capsys.readouterr()
    assert "失败项" in captured.err
    assert "pdf_to_image" in captured.err


def test_batch_cli_success_exit_code(monkeypatch, stubbed_pipeline, run_dir, capsys):
    monkeypatch.setattr(batch_process, "QuestionOCREngine", lambda mode="combined": StubEngine(mode=mode))
    monkeypatch.setattr(batch_process, "check_dependencies", lambda: None)

    exit_code = batch_process.main([stubbed_pipeline, "-o", run_dir, "--log-level", "ERROR"])
    assert exit_code == 0
    manifest = read_json(os.path.join(run_dir, "manifest.json"))
    assert manifest["success"] is True
    assert "4 题" in capsys.readouterr().out


def test_batch_cli_dependency_error_exit_code(monkeypatch, pdf, run_dir, capsys):
    """依赖缺失时不生成运行产物，退出码区分于流程内失败"""
    monkeypatch.setattr(batch_process, "check_dependencies", lambda: "缺少 poppler-utils")
    exit_code = batch_process.main([pdf, "-o", run_dir])
    assert exit_code == 2
    assert "依赖检查未通过" in capsys.readouterr().err
    assert not os.path.exists(os.path.join(run_dir, "manifest.json"))


def test_batch_cli_clear_removes_previous_output(monkeypatch, pdf, run_dir):
    """--clear 删除整个输出目录，默认只清理本流程产物"""
    PDFAnalyzer = load_analyzer()
    monkeypatch.setattr(batch_process, "QuestionOCREngine", lambda mode="combined": StubEngine(mode=mode))
    monkeypatch.setattr(batch_process, "check_dependencies", lambda: None)

    def fake_rasterize(pdf_path, output_dir, dpi):
        os.makedirs(output_dir, exist_ok=True)
        target = os.path.join(output_dir, "page_1.png")
        make_page_image(target)
        return 1, [(1, target)]

    monkeypatch.setattr(batch_process, "rasterize_pages", fake_rasterize)
    monkeypatch.setattr(PDFAnalyzer, "detect_question_boundaries",
                        lambda self, image_path: [(60, 100, 460, 200)])

    stale = os.path.join(run_dir, "user_note.txt")
    os.makedirs(run_dir, exist_ok=True)
    with open(stale, "w", encoding="utf-8") as handle:
        handle.write("keep me")

    assert batch_process.main([pdf, "-o", run_dir, "--log-level", "ERROR"]) == 0
    assert os.path.exists(stale)

    assert batch_process.main([pdf, "-o", run_dir, "--clear", "--log-level", "ERROR"]) == 0
    assert not os.path.exists(stale)


# ---------------------------------------------------------------------------
# pdf_analyzer 兼容性
# ---------------------------------------------------------------------------


def test_pdf_analyzer_public_defaults_unchanged(tmp_path):
    """pdf_analyzer 既有公开行为保持不变：默认仍写 extracted_questions/"""
    PDFAnalyzer = load_analyzer()
    page = str(tmp_path / "page_1.png")
    make_page_image(page)
    cwd = os.getcwd()
    try:
        os.chdir(str(tmp_path))
        analyzer = PDFAnalyzer(str(tmp_path / "不存在.pdf"))
        assert isinstance(analyzer.detect_question_boundaries(page), list)

        extracted = analyzer.extract_questions(page, [(60, 100, 460, 200)], 1)
        assert extracted == [os.path.join("extracted_questions", "page_1_question_1.png")]
        assert os.path.isfile(os.path.join(str(tmp_path), "extracted_questions", "page_1_question_1.png"))

        named = analyzer.extract_questions(page, [(60, 100, 460, 200)], 2,
                                           output_dir=str(tmp_path / "custom"))
        assert named == [os.path.join(str(tmp_path / "custom"), "page_2_question_1.png")]
        assert analyzer.detect_question_boundaries(str(tmp_path / "没有这个文件.png")) == []
    finally:
        os.chdir(cwd)
