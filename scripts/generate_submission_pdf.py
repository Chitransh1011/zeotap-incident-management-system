from __future__ import annotations

import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GITHUB_URL = os.getenv("GITHUB_URL", "https://github.com/Chitransh1011/zeotap-incident-management-system")
INPUT_PATH = ROOT / "docs" / "SUBMISSION.md"
OUTPUT_PATH = ROOT / "Chitransh Prasanna - Infrastructure - SRE Intern Assignment.pdf"


def main() -> None:
    markdown = INPUT_PATH.read_text(encoding="utf-8").replace("TODO_REPLACE_WITH_GITHUB_LINK", GITHUB_URL)
    lines = markdown_to_lines(markdown)
    write_pdf(OUTPUT_PATH, lines)
    print(f"Created {OUTPUT_PATH}")


def markdown_to_lines(markdown: str) -> list[str]:
    result: list[str] = []
    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()
        for prefix in ("###### ", "##### ", "#### ", "### ", "## ", "# "):
            if line.startswith(prefix):
                line = line[len(prefix) :]
                break
        if line.startswith("- "):
            line = "  - " + line[2:]
        line = line.replace("`", "").replace("**", "")
        if line in {"```bash", "```powershell", "```text", "```"}:
            continue
        if not line:
            result.append("")
            continue
        result.extend(wrap(line, 92))
    return result


def wrap(line: str, width: int) -> list[str]:
    if len(line) <= width:
        return [line]
    words = line.split(" ")
    output: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) > width:
            output.append(current)
            current = word
        else:
            current = candidate
    if current:
        output.append(current)
    return output


def write_pdf(path: Path, all_lines: list[str]) -> None:
    objects: list[str] = []
    pages: list[str] = []
    first_dynamic_object_number = 5
    lines_per_page = 46

    for index in range(0, len(all_lines), lines_per_page):
        page_lines = all_lines[index : index + lines_per_page]
        content = render_page(page_lines)
        content_number = first_dynamic_object_number + len(objects)
        objects.append(f"<< /Length {len(content.encode('utf-8'))} >>\nstream\n{content}\nendstream")
        page_number = first_dynamic_object_number + len(objects)
        objects.append(
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents {content_number} 0 R >>"
        )
        pages.append(f"{page_number} 0 R")

    final_objects = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        f"<< /Type /Pages /Kids [{' '.join(pages)}] /Count {len(pages)} >>",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>",
        *objects,
    ]

    pdf = "%PDF-1.4\n"
    offsets = [0]
    for number, obj in enumerate(final_objects, start=1):
        offsets.append(len(pdf.encode("utf-8")))
        pdf += f"{number} 0 obj\n{obj}\nendobj\n"
    xref_offset = len(pdf.encode("utf-8"))
    pdf += f"xref\n0 {len(final_objects) + 1}\n"
    pdf += "0000000000 65535 f \n"
    for offset in offsets[1:]:
        pdf += f"{offset:010} 00000 n \n"
    pdf += f"trailer\n<< /Size {len(final_objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n"
    path.write_text(pdf, encoding="latin-1")


def render_page(lines: list[str]) -> str:
    commands = ["BT", "/F1 10 Tf", "50 752 Td", "14 TL"]
    for line in lines:
        if not line:
            commands.append("T*")
            continue
        is_heading = not line.startswith(" ") and line[:1].isalnum() and len(line) < 70
        commands.append("/F2 11 Tf" if is_heading else "/F1 10 Tf")
        commands.append(f"({escape_pdf(line)}) Tj")
        commands.append("T*")
    commands.append("ET")
    return "\n".join(commands)


def escape_pdf(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


if __name__ == "__main__":
    main()
