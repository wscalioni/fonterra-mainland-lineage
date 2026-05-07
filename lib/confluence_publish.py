"""Markdown → Confluence storage XHTML for the UC Lineage Spider-Web page.

Targeted at the markdown shapes produced by uc-lineage-spiderweb.md, not a
general-purpose md2storage. Handles:

- Headings (#, ##, ###) → <h1>, <h2>, <h3>
- Pipe tables (incl. alignment row)        → <table><tbody><tr>... with th in first row
- Bullet lists (- )                        → <ul><li>...</li></ul>
- Bold **x**, italic *x*, inline `code`    → <strong>, <em>, <code>
- Fenced code blocks ```...```             → <ac:structured-macro ac:name="code">...
- Links [text](url)                        → <a href="url">text</a>
- Image refs ![alt](path)                  → <ac:image><ri:attachment ri:filename="..."/></ac:image>
                                             (filename = basename of path)
- Horizontal rules ---                     → <hr/>
- Paragraphs (blank-line separated)        → <p>...</p>

Storage-format gotchas applied (per Will's memory):
- Raw XHTML string (not wrapped in CDATA, no doctype/footer)
- All tags properly closed (<br/> not <br>, etc.)
- Never emit <ac:plain-text-link-body> — bare <a href="..."> only
- Wide ASCII art is never produced (no <pre> for tables; only for fenced code)
"""
from __future__ import annotations

import html
import os
import re
from pathlib import Path


def md_to_storage(md: str) -> str:
    lines = md.replace("\r\n", "\n").split("\n")
    out: list[str] = []
    i = 0
    in_para: list[str] = []

    def flush_para():
        if in_para:
            text = " ".join(in_para).strip()
            if text:
                out.append(f"<p>{_inline(text)}</p>")
            in_para.clear()

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Fenced code block — use <pre><code>...</code></pre> with HTML-escape
        # (no CDATA, no ac:structured-macro, per memory). Lines must be <70 chars
        # to avoid Confluence's wide-pre-block rendering bug.
        if stripped.startswith("```"):
            flush_para()
            i += 1
            buf = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                buf.append(lines[i]); i += 1
            i += 1
            body = html.escape("\n".join(buf))
            out.append(f"<pre><code>{body}</code></pre>")
            continue

        # Heading
        m = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if m:
            flush_para()
            level = len(m.group(1))
            out.append(f"<h{level}>{_inline(m.group(2))}</h{level}>")
            i += 1
            continue

        # Horizontal rule
        if re.match(r"^-{3,}$", stripped):
            flush_para()
            out.append("<hr/>")
            i += 1
            continue

        # Pipe table
        if "|" in stripped and i + 1 < len(lines) and re.match(r"^\s*\|?[\s:|-]+\|[\s:|-]+\|?\s*$", lines[i + 1]):
            flush_para()
            tbl = []
            while i < len(lines) and "|" in lines[i] and lines[i].strip():
                tbl.append(lines[i])
                i += 1
            out.append(_render_table(tbl))
            continue

        # Bullet list
        if re.match(r"^- ", stripped):
            flush_para()
            items: list[str] = []
            while i < len(lines) and re.match(r"^- ", lines[i].strip()):
                items.append(lines[i].strip()[2:])
                i += 1
            out.append("<ul>" + "".join(f"<li>{_inline(it)}</li>" for it in items) + "</ul>")
            continue

        # Image-only line (paragraph image)
        m = re.match(r"^!\[(?P<alt>[^\]]*)\]\((?P<path>[^)]+)\)\s*$", stripped)
        if m:
            flush_para()
            filename = os.path.basename(m.group("path"))
            alt = html.escape(m.group("alt"))
            out.append(
                '<ac:image ac:width="900" ac:align="center" ac:alt="' + alt + '">'
                f'<ri:attachment ri:filename="{filename}"/>'
                '</ac:image>'
            )
            i += 1
            continue

        # Blank line — paragraph break
        if not stripped:
            flush_para()
            i += 1
            continue

        # Otherwise accumulate paragraph
        in_para.append(stripped)
        i += 1

    flush_para()
    return "\n".join(out)


def _inline(text: str) -> str:
    """Inline markdown → storage HTML, applied AFTER block-level handling."""
    # Inline image (rare in our doc, but supported).
    text = re.sub(
        r"!\[(?P<alt>[^\]]*)\]\((?P<path>[^)]+)\)",
        lambda m: (
            '<ac:image ac:height="200" ac:alt="' + html.escape(m.group("alt")) + '">'
            f'<ri:attachment ri:filename="{os.path.basename(m.group("path"))}"/>'
            '</ac:image>'
        ),
        text,
    )
    # Inline code FIRST so we don't mangle ** inside `code`.
    parts: list[str] = []
    last = 0
    for m in re.finditer(r"`([^`]+)`", text):
        parts.append(_format_text(text[last:m.start()]))
        parts.append(f"<code>{html.escape(m.group(1))}</code>")
        last = m.end()
    parts.append(_format_text(text[last:]))
    return "".join(parts)


def _format_text(text: str) -> str:
    """Apply bold, italic, links to a chunk that contains no inline code."""
    # Escape HTML special chars.
    text = (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;"))
    # Links — bare <a href="..."> per memory gotcha (no ac:plain-text-link-body).
    text = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        lambda m: f'<a href="{m.group(2)}">{m.group(1)}</a>',
        text,
    )
    # Bold (greedy match across **x**)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    # Italic — match _x_ or *x* but only outside word boundaries to avoid mangling.
    text = re.sub(r"(?<!\w)\*([^*\s][^*]*?[^*\s]|[^*\s])\*(?!\w)", r"<em>\1</em>", text)
    return text


def _render_table(rows: list[str]) -> str:
    # Strip leading / trailing pipes; split.
    grid = []
    for r in rows:
        cells = [c.strip() for c in r.strip().strip("|").split("|")]
        grid.append(cells)
    # Drop alignment row (second row, all dashes/colons).
    if len(grid) >= 2 and all(re.match(r"^[\s:|-]+$", c) for c in grid[1]):
        header, body = grid[0], grid[2:]
    else:
        header, body = grid[0], grid[1:]
    parts = ["<table><tbody>"]
    parts.append("<tr>" + "".join(f"<th>{_inline(c)}</th>" for c in header) + "</tr>")
    for r in body:
        parts.append("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in r) + "</tr>")
    parts.append("</tbody></table>")
    return "".join(parts)


# ---------------------------------------------------------------------------
# Page-build helpers

def build_storage_xhtml(md_path: Path, *, drop_top_h1: bool = True) -> str:
    md = md_path.read_text()
    if drop_top_h1:
        # Confluence renders the page title separately; remove the leading #.
        md = re.sub(r"^# [^\n]+\n+", "", md, count=1)
    return md_to_storage(md)


if __name__ == "__main__":
    import sys
    p = Path(sys.argv[1] if len(sys.argv) > 1 else "analysis/uc-lineage-spiderweb.md")
    print(build_storage_xhtml(p))
