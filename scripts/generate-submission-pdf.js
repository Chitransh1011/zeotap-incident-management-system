import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("..", import.meta.url));
const githubUrl = process.env.GITHUB_URL ?? "TODO_REPLACE_WITH_GITHUB_LINK";
const inputPath = path.join(root, "docs", "SUBMISSION.md");
const outputPath = path.join(root, "Chitransh Prasanna - Infrastructure - SRE Intern Assignment.pdf");

const markdown = fs.readFileSync(inputPath, "utf8").replace("TODO_REPLACE_WITH_GITHUB_LINK", githubUrl);
const lines = markdownToLines(markdown);
writePdf(outputPath, lines);
console.log(`Created ${outputPath}`);

function markdownToLines(markdownText) {
  const result = [];
  for (const rawLine of markdownText.split(/\r?\n/)) {
    let line = rawLine
      .replace(/^#{1,6}\s*/, "")
      .replace(/^-\s*/, "  - ")
      .replace(/`/g, "")
      .replace(/\*\*/g, "")
      .trimEnd();
    if (line === "```bash" || line === "```powershell" || line === "```text" || line === "```") {
      continue;
    }
    if (line.length === 0) {
      result.push("");
      continue;
    }
    result.push(...wrap(line, 92));
  }
  return result;
}

function wrap(line, width) {
  if (line.length <= width) {
    return [line];
  }
  const words = line.split(" ");
  const output = [];
  let current = "";
  for (const word of words) {
    if ((current + " " + word).trim().length > width) {
      output.push(current);
      current = word;
    } else {
      current = `${current} ${word}`.trim();
    }
  }
  if (current) {
    output.push(current);
  }
  return output;
}

function writePdf(filePath, allLines) {
  const objects = [];
  const pages = [];
  const linesPerPage = 46;
  const firstDynamicObjectNumber = 5;
  for (let i = 0; i < allLines.length; i += linesPerPage) {
    const pageLines = allLines.slice(i, i + linesPerPage);
    const content = renderPage(pageLines);
    const contentObjectNumber = firstDynamicObjectNumber + objects.length;
    objects.push(`<< /Length ${Buffer.byteLength(content)} >>\nstream\n${content}\nendstream`);
    const pageObjectNumber = firstDynamicObjectNumber + objects.length;
    objects.push(`<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents ${contentObjectNumber} 0 R >>`);
    pages.push(`${pageObjectNumber} 0 R`);
  }

  const catalog = "<< /Type /Catalog /Pages 2 0 R >>";
  const pagesObject = `<< /Type /Pages /Kids [${pages.join(" ")}] /Count ${pages.length} >>`;
  const fontRegular = "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>";
  const fontBold = "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>";
  const finalObjects = [catalog, pagesObject, fontRegular, fontBold, ...objects];

  let pdf = "%PDF-1.4\n";
  const offsets = [0];
  finalObjects.forEach((object, index) => {
    offsets.push(Buffer.byteLength(pdf));
    pdf += `${index + 1} 0 obj\n${object}\nendobj\n`;
  });
  const xrefOffset = Buffer.byteLength(pdf);
  pdf += `xref\n0 ${finalObjects.length + 1}\n`;
  pdf += "0000000000 65535 f \n";
  for (let i = 1; i < offsets.length; i += 1) {
    pdf += `${String(offsets[i]).padStart(10, "0")} 00000 n \n`;
  }
  pdf += `trailer\n<< /Size ${finalObjects.length + 1} /Root 1 0 R >>\nstartxref\n${xrefOffset}\n%%EOF\n`;
  fs.writeFileSync(filePath, pdf);
}

function renderPage(lines) {
  const commands = ["BT", "/F1 10 Tf", "50 752 Td", "14 TL"];
  for (const line of lines) {
    if (line.length === 0) {
      commands.push("T*");
      continue;
    }
    const isHeading = !line.startsWith(" ") && /^[A-Z0-9].*/.test(line) && line.length < 70;
    commands.push(isHeading ? "/F2 11 Tf" : "/F1 10 Tf");
    commands.push(`(${escapePdf(line)}) Tj`);
    commands.push("T*");
  }
  commands.push("ET");
  return commands.join("\n");
}

function escapePdf(text) {
  return text.replace(/\\/g, "\\\\").replace(/\(/g, "\\(").replace(/\)/g, "\\)");
}
