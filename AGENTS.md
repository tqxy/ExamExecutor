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
