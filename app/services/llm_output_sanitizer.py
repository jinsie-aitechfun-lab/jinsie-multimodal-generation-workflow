from __future__ import annotations

import ast
import json
import re
from typing import Any, Dict, Optional


_CODE_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL | re.IGNORECASE)
_FIRST_JSON_BLOCK_RE = re.compile(r"(\{.*\}|\[.*\])", re.DOTALL)


def strip_code_fences(text: str) -> str:
    t = (text or "").strip()
    if not t:
        return ""
    m = _CODE_FENCE_RE.search(t)
    if m:
        return (m.group(1) or "").strip()
    return t


def normalize_quotes(text: str) -> str:
    t = (text or "")
    if not t:
        return ""
    # 常见中英文引号统一
    t = t.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    # 清理 BOM/空字符
    t = t.replace("\ufeff", "").replace("\u0000", "")
    return t.strip()


def _safe_json_loads(s: str) -> Optional[Any]:
    try:
        return json.loads(s)
    except Exception:
        return None


def _safe_literal_eval(s: str) -> Optional[Any]:
    try:
        return ast.literal_eval(s)
    except Exception:
        return None


def _extract_first_json_like(text: str) -> Optional[str]:
    if not text:
        return None
    m = _FIRST_JSON_BLOCK_RE.search(text)
    if not m:
        return None
    return (m.group(1) or "").strip()


def extract_json_field(content: str, key: str = "text") -> Optional[str]:
    """
    从可能是 JSON / python dict / 被 code-fence 包裹 / 混杂文本 的 content 中抽取字段值。
    支持：
    - {"title":..,"summary":..,"text":..}
    - {'1': '...', '2': '...'} 这种数字键段落（会在 extract_story_text 里处理）
    - {"paragraphs":[{"sentence":"..."}]} 或 {" paragraphs":[{" sentence":"..."}]}
    """
    raw = normalize_quotes(strip_code_fences(content))
    if not raw:
        return None

    obj = _safe_json_loads(raw)
    if obj is None:
        block = _extract_first_json_like(raw)
        if block:
            obj = _safe_json_loads(block)

    if obj is None:
        obj = _safe_literal_eval(raw)
        if obj is None:
            block = _extract_first_json_like(raw)
            if block:
                obj = _safe_literal_eval(block)

    if isinstance(obj, dict):
        val = obj.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    return None


def extract_story_text(content: str) -> Optional[str]:
    """
    尽量把 LLM 的输出抽成“纯故事正文”：
    - 如果是 JSON，取 text
    - 如果是 python dict 数字键段落 {'1': '...', '2': '...'}，按序拼接
    - 如果是 paragraphs sentence 列表，拼接 sentence
    - 否则当作纯文本（但如果开头像结构体 { 或 [，返回 None 让上层 fallback）
    """
    raw = normalize_quotes(strip_code_fences(content))
    if not raw:
        return None

    # 1) 直接取 text 字段
    txt = extract_json_field(raw, "text")
    if isinstance(txt, str) and txt.strip():
        return txt.strip()

    # 2) 尝试解析整体为对象，再做更多结构识别
    obj = _safe_json_loads(raw)
    if obj is None:
        block = _extract_first_json_like(raw)
        if block:
            obj = _safe_json_loads(block)

    if obj is None:
        obj = _safe_literal_eval(raw)
        if obj is None:
            block = _extract_first_json_like(raw)
            if block:
                obj = _safe_literal_eval(block)

    # 2.1 dict 数字键段落
    if isinstance(obj, dict):
        numbered = []
        for k, v in obj.items():
            if isinstance(k, str) and k.strip().isdigit() and isinstance(v, str) and v.strip():
                numbered.append((int(k.strip()), v.strip()))
        if numbered:
            numbered.sort(key=lambda x: x[0])
            return "\n".join([v for _, v in numbered]).strip()

        # 2.2 paragraphs sentence
        paras = obj.get("paragraphs") or obj.get(" paragraphs")
        if isinstance(paras, list):
            lines = []
            for it in paras:
                if isinstance(it, dict):
                    s = it.get("sentence") or it.get(" sentence") or it.get("text") or it.get(" content")
                    if isinstance(s, str) and s.strip():
                        lines.append(s.strip())
            if lines:
                return "\n".join(lines).strip()

    # 3) 最后当作纯文本
    plain = raw.strip()
    head = plain.lstrip()[:1]
    if head in ("{", "["):
        return None
    return plain


def parse_story_payload(content: str, *, topic: str) -> Optional[Dict[str, str]]:
    """
    统一返回 story 的三字段：title/summary/text。
    - title/summary 若 JSON 里拿不到，就用轻量 fallback
    - text 必须能抽到（否则返回 None 让上层走模板 fallback）
    """
    raw = normalize_quotes(strip_code_fences(content))
    if not raw:
        return None

    topic_fallback = (topic or "").strip() or "一个温暖的童话故事"

    # 优先从结构中抽
    title = extract_json_field(raw, "title") or f"{topic_fallback}的故事"
    summary = extract_json_field(raw, "summary") or f"一个围绕“{topic_fallback}”展开的短篇故事。"
    text = extract_story_text(raw)
    if not text:
        return None

    return {
        "title": title.strip(),
        "summary": summary.strip(),
        "text": text.strip(),
    }
