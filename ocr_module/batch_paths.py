#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
归档路径与运行目录布局
统一归档 JSON 里的路径写法：优先仓库相对路径，其次运行目录相对路径，全部使用正斜杠分隔符
"""

import os
from typing import Any, Iterable, List, Optional, Tuple

SEPARATOR = '/'

# 批量流程运行目录布局
PAGE_IMAGES_DIR = 'page_images'
QUESTION_IMAGES_DIR = 'question_images'
OCR_JSON_DIR = 'ocr_json'
MANIFEST_FILE = 'manifest.json'
ERRORS_FILE = 'errors.json'
RESTORED_FILE = 'restored_questions.json'


def repo_root() -> str:
    """仓库根目录（本文件位于 <repo>/ocr_module/ 下）"""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def default_archive_roots(run_dir: Optional[str] = None) -> Tuple[str, ...]:
    """归档相对路径的基准目录：仓库根目录优先，其次运行目录"""
    roots: List[str] = [repo_root()]
    if run_dir:
        roots.append(os.path.abspath(run_dir))
    roots.append(os.getcwd())
    return tuple(roots)


def _relative_to(abs_path: str, root: str) -> Optional[str]:
    """abs_path 位于 root 内时返回相对 root 的正斜杠路径，否则返回 None"""
    try:
        rel = os.path.relpath(abs_path, os.path.abspath(root))
    except ValueError:
        # Windows 跨盘符无法求相对路径
        return None

    if rel == os.curdir:
        return None

    parts = rel.split(os.sep)
    if parts and parts[0] == os.pardir:
        return None

    return rel.replace(os.sep, SEPARATOR)


def to_archive_path(path: Any, roots: Iterable[str] = ()) -> str:
    """把 path 转成归档内使用的正斜杠路径

    Args:
        path: 待转换的路径，str 或 os.PathLike
        roots: 依次尝试的基准目录，通常先仓库根目录、再本次运行目录

    Returns:
        str: 第一个命中基准目录的相对路径；都不命中时返回绝对路径的正斜杠写法
    """
    if path is None:
        return ''

    text = os.fspath(path) if hasattr(path, '__fspath__') else str(path)
    if not text:
        return ''

    abs_path = os.path.abspath(text)
    root_list = list(roots) or [repo_root()]
    for root in root_list:
        rel = _relative_to(abs_path, root)
        if rel is not None:
            return rel

    return abs_path.replace(os.sep, SEPARATOR)


def resolve_archive_path(path: str, roots: Iterable[str] = ()) -> str:
    """把归档路径还原成实际文件路径

    Args:
        path: 绝对路径或归档相对路径
        roots: 依次尝试拼接的基准目录

    Returns:
        str: 优先返回存在的文件路径，都不存在时返回按第一个基准目录拼接的结果
    """
    if not path:
        return path

    if os.path.isabs(path) and os.path.exists(path):
        return path

    root_list = list(roots) or [os.getcwd()]
    for root in root_list:
        candidate = os.path.join(root, path.replace(SEPARATOR, os.sep))
        if os.path.exists(candidate):
            return candidate

    return os.path.join(root_list[0], path.replace(SEPARATOR, os.sep))


def normalize_paths(payload: Any, roots: Iterable[str] = ()) -> Any:
    """递归把 dict/list 中形如 ``xxx_path`` 的字段值转换为归档路径

    Args:
        payload: 待处理的数据结构
        roots: 传给 to_archive_path 的基准目录

    Returns:
        处理后的数据结构（原地修改并返回）
    """
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key.endswith('_path') and isinstance(value, (str, os.PathLike)):
                payload[key] = to_archive_path(value, roots)
            else:
                normalize_paths(value, roots)
    elif isinstance(payload, list):
        for item in payload:
            normalize_paths(item, roots)

    return payload


def join_parts(*parts: Any) -> str:
    """用正斜杠拼接归档路径片段"""
    cleaned: List[str] = []
    for part in parts:
        if not part:
            continue
        text = str(part).replace(os.sep, SEPARATOR).strip(SEPARATOR)
        if text:
            cleaned.append(text)

    return SEPARATOR.join(cleaned)
