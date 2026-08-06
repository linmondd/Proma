#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从 chapters/*.md 重建合订 MD / DOCX / EPUB。"""

from __future__ import annotations

import html
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHAP_DIR = ROOT / "chapters"
OUT_MD = ROOT / "粉色真迹·练舞室.md"
OUT_DOCX = ROOT / "粉色真迹·练舞室.docx"
OUT_EPUB = ROOT / "粉色真迹·练舞室.epub"
ARTIFACT = Path("/opt/cursor/artifacts/粉色真迹·练舞室.epub")

CN_NUM = "零一二三四五六七八九十"


def chapter_title_cn(n: int, raw_title: str) -> str:
    if n <= 10:
        cn = CN_NUM[n]
    elif n < 20:
        cn = "十" + (CN_NUM[n - 10] if n > 10 else "")
    else:
        cn = CN_NUM[n // 10] + "十" + (CN_NUM[n % 10] if n % 10 else "")
    return f"第{cn}章 {raw_title}"


def load_chapters() -> list[tuple[int, str, str]]:
    files = sorted(CHAP_DIR.glob("*.md"))
    out = []
    for i, p in enumerate(files, 1):
        text = p.read_text(encoding="utf-8").strip() + "\n"
        # 文件名: 01-标题.md
        m = re.match(r"\d+-(.+)\.md$", p.name)
        raw = m.group(1) if m else p.stem
        # 若正文首行是 # 标题则用它
        hm = re.match(r"^#\s+(.+)\n", text)
        if hm:
            title_line = hm.group(1).strip()
            # 去掉可能的「第X章」前缀，只留副题
            raw2 = re.sub(r"^第[零一二三四五六七八九十百\d]+章\s*", "", title_line)
            body = text[hm.end() :]
            title = chapter_title_cn(i, raw2)
        else:
            title = chapter_title_cn(i, raw)
            body = text
        out.append((i, title, body.strip() + "\n"))
    return out


def md_to_paragraphs(body: str) -> list[str]:
    parts = re.split(r"\n\s*\n", body.strip())
    paras = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if part == "---":
            continue
        # 行内换行并成空格
        part = re.sub(r"\n+", " ", part)
        paras.append(part)
    return paras


def build_md(chapters: list[tuple[int, str, str]]) -> None:
    chunks = [
        "# 粉色真迹·练舞室\n",
        "\n",
        "> 黄文精修版（v10）。道具对齐全身清脸；场景增补；弱章手写密写。\n",
        "\n",
    ]
    for i, title, body in chapters:
        chunks.append(f"# {title}\n\n")
        for para in md_to_paragraphs(body):
            chunks.append(para + "\n\n")
        chunks.append("\n")
    OUT_MD.write_text("".join(chunks), encoding="utf-8")
    print("MD", OUT_MD, "bytes", OUT_MD.stat().st_size)


def build_docx() -> None:
    import subprocess

    subprocess.check_call(
        ["pandoc", str(OUT_MD), "-o", str(OUT_DOCX), "--from=markdown", "--to=docx"]
    )
    print("DOCX", OUT_DOCX, "bytes", OUT_DOCX.stat().st_size)


def chapter_xhtml(title: str, body: str) -> bytes:
    paras = md_to_paragraphs(body)
    p_html = "\n".join(f"<p>\n{html.escape(p)}\n</p>" for p in paras)
    doc = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="zh-CN" lang="zh-CN">
<head><meta charset="utf-8"/><title>{html.escape(title)}</title><link rel="stylesheet" href="../style/book.css"/></head><body>
<h1>{html.escape(title)}</h1>
{p_html}
</body></html>
"""
    return doc.encode("utf-8")


def build_epub(chapters: list[tuple[int, str, str]]) -> None:
    import io
    import shutil
    import tempfile

    tmp = Path(tempfile.mkdtemp(prefix="epub-rebuild-"))
    try:
        with zipfile.ZipFile(OUT_EPUB, "r") as zin:
            zin.extractall(tmp)

        # update chapters
        for i, title, body in chapters:
            path = tmp / "EPUB" / "chapters" / f"c{i:02d}.xhtml"
            path.write_bytes(chapter_xhtml(title, body))

        # bump version metadata
        opf = tmp / "EPUB" / "content.opf"
        opf_text = opf.read_text(encoding="utf-8")
        opf_text = re.sub(
            r"urn:pink-syringe:v\d+", "urn:pink-syringe:v10", opf_text
        )
        opf_text = re.sub(
            r"<dc:description>.*?</dc:description>",
            "<dc:description>黄文精修版 v10。道具对齐全身清脸；场景增补；弱章手写密写。</dc:description>",
            opf_text,
            count=1,
            flags=re.S,
        )
        opf.write_text(opf_text, encoding="utf-8")

        # repack: mimetype first, stored
        out_buf = io.BytesIO()
        with zipfile.ZipFile(out_buf, "w") as zout:
            # mimetype stored
            mime = (tmp / "mimetype").read_bytes()
            zout.writestr("mimetype", mime, compress_type=zipfile.ZIP_STORED)
            for f in sorted(tmp.rglob("*")):
                if f.is_dir():
                    continue
                rel = f.relative_to(tmp).as_posix()
                if rel == "mimetype":
                    continue
                zout.write(f, rel, compress_type=zipfile.ZIP_DEFLATED)
        OUT_EPUB.write_bytes(out_buf.getvalue())
        ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(OUT_EPUB, ARTIFACT)
        print("EPUB", OUT_EPUB, "bytes", OUT_EPUB.stat().st_size)
        print("ARTIFACT", ARTIFACT, "bytes", ARTIFACT.stat().st_size)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> None:
    chapters = load_chapters()
    print("chapters", len(chapters))
    build_md(chapters)
    build_docx()
    build_epub(chapters)


if __name__ == "__main__":
    main()
