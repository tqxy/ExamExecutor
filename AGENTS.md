# ExamExecutor developer guide

## Repository layout

- `ocr_module/src/`: OCR processing implementation.
- `ocr_module/latex_to_image/`: LaTeX rendering implementation and lightweight tests.
- `ocr_module/src/test/`: OCR scripts that may require models or local fixtures.
- `doc/`: Product and architecture documents.

## Required pull request checks

Run the same smoke gate as GitHub Actions:

```bash
python -m pip install -r ocr_module/latex_to_image/requirements.txt
python -m compileall -q ocr_module
python -m pytest -q ocr_module/latex_to_image/test_converter.py
```

Add focused tests for changed behavior. Do not treat scripts that only print results as proof of correctness; use assertions where practical.

## External resources

The default gate intentionally does not download OCR models or depend on local PDF files. Tests requiring Paddle OCR, Pix2Text, external services, or local documents must use explicit fixtures and must not block the lightweight gate with machine-specific paths.

## Generated files

Do not commit generated OCR output, rendered images, virtual environments, caches, or test artifacts unless the issue explicitly requires a fixture. Keep changes scoped to the issue and preserve the existing `master` branch behavior.

## Language policy

- Issue 评论、分诊内容、PR 标题和描述、review 正文均使用简体中文。
- 代码标识符、命令、文件路径和技术术语保持原文。
- 不得翻译或修改自动化使用的标签、HTML markers 和 AI disclosure。
- Review 结尾的机器判定行必须保持为 `✅ APPROVED` 或 `🔄 CHANGES REQUESTED`。
