import re
import shutil
import subprocess
import zipfile
from dataclasses import dataclass
from html import unescape
from pathlib import Path
from xml.etree import ElementTree

TEXT_EXTENSIONS = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt"}
PENDING_ENHANCEMENT_EXTENSIONS = {".png", ".jpg", ".jpeg", ".dwg", ".dxf"}


@dataclass(frozen=True)
class DocumentAnalysis:
    document_role: str
    assigned_modules: list[str]
    parse_status: str
    extracted_text: str
    error_message: str = ""


def analyze_document(filename: str, stored_path: str, project_context: dict[str, str] | None = None) -> DocumentAnalysis:
    suffix = Path(filename).suffix.lower()
    context_text = " ".join((project_context or {}).values())

    if suffix in PENDING_ENHANCEMENT_EXTENSIONS:
        role, modules = classify_document(filename, "", context_text)
        return DocumentAnalysis(
            document_role=role,
            assigned_modules=modules,
            parse_status="pending_enhancement",
            extracted_text="",
            error_message="图片或 CAD 文件当前返回 pending_enhancement，暂不做增强解析。",
        )

    try:
        extracted_text = extract_text(Path(stored_path), suffix)
    except Exception as exc:
        role, modules = classify_document(filename, "", context_text)
        return DocumentAnalysis(
            document_role=role,
            assigned_modules=modules,
            parse_status="failed",
            extracted_text="",
            error_message=str(exc),
        )

    role, modules = classify_document(filename, extracted_text, context_text)
    return DocumentAnalysis(
        document_role=role,
        assigned_modules=modules,
        parse_status="parsed" if suffix in TEXT_EXTENSIONS else "pending_enhancement",
        extracted_text=extracted_text,
    )


def extract_text(path: Path, suffix: str) -> str:
    if suffix == ".pdf":
        return _extract_pdf_text(path)
    if suffix in {".docx", ".xlsx", ".pptx"}:
        return _extract_office_open_xml(path, suffix)
    return _extract_loose_text(path)


def classify_document(filename: str, extracted_text: str, context_text: str = "") -> tuple[str, list[str]]:
    haystack = _normalize_text(f"{filename} {extracted_text} {context_text}")

    if _has_any(haystack, ["企业", "公司介绍", "资质", "荣誉", "cnas", "专利", "产能", "证书"]):
        return "enterprise_material", ["M6"]
    if _has_any(haystack, ["案例", "case", "业绩", "同类型", "已完工", "示范工程"]):
        return "case_material", ["M5"]
    if _has_any(haystack, ["图纸", "总平面图", "平面图", "立面图", "剖面图", "cad", "dwg", "dxf", "drawing"]):
        return "drawing", ["M1", "M2"]
    if _has_any(haystack, ["招标", "投标", "标书", "tender", "技术标准", "技术规范", "采购文件"]):
        return "tender", ["M1", "M2", "M5"]
    if _has_any(haystack, ["调研", "现场踏勘", "勘察", "survey", "痛点", "施工窗口", "降噪需求", "需求分析"]):
        return "survey", ["M2", "M5"]
    if _has_any(haystack, ["简介", "概况", "项目", "工程", "brief", "地铁", "轨道交通", "铁路", "公路", "高速", "声屏障"]):
        return "project_brief", ["M1", "M2", "M5"]
    return "unknown", []


def _extract_office_open_xml(path: Path, suffix: str) -> str:
    prefixes = {
        ".docx": ("word/",),
        ".xlsx": ("xl/sharedStrings.xml", "xl/worksheets/"),
        ".pptx": ("ppt/slides/",),
    }[suffix]
    chunks: list[str] = []
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            if not name.endswith(".xml") or not name.startswith(prefixes):
                continue
            xml_text = archive.read(name).decode("utf-8", errors="ignore")
            chunks.extend(_xml_text_nodes(xml_text))
    return _compact_text(" ".join(chunks))


def _xml_text_nodes(xml_text: str) -> list[str]:
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError:
        return _strip_xml_tags(xml_text)
    values: list[str] = []
    for node in root.iter():
        if node.text and node.text.strip():
            values.append(node.text.strip())
    return values


def _strip_xml_tags(xml_text: str) -> list[str]:
    text = re.sub(r"<[^>]+>", " ", xml_text)
    return [unescape(text)]


def _extract_pdf_text(path: Path) -> str:
    pdftotext = shutil.which("pdftotext")
    if pdftotext:
        try:
            result = subprocess.run(
                [pdftotext, "-layout", "-enc", "UTF-8", str(path), "-"],
                capture_output=True,
                encoding="utf-8",
                errors="ignore",
                text=True,
                timeout=30,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            result = None
        if result and result.returncode == 0 and result.stdout.strip():
            return _compact_text(result.stdout)
    return _extract_loose_text(path)


def _extract_loose_text(path: Path) -> str:
    data = path.read_bytes()
    decoded = data.decode("utf-8", errors="ignore")
    if not decoded.strip():
        decoded = data.decode("latin-1", errors="ignore")
    text = re.sub(r"\\[()\\]", " ", decoded)
    text = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff，。；：、（）《》【】_\-]+", " ", text)
    return _compact_text(text)


def _normalize_text(text: str) -> str:
    return _compact_text(text).lower()


def _compact_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _has_any(text: str, keywords: list[str]) -> bool:
    return any(keyword.lower() in text for keyword in keywords)
