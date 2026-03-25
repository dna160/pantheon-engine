import { NextRequest, NextResponse } from "next/server";
import {
  Document, Packer, Paragraph, TextRun, HeadingLevel,
  AlignmentType, BorderStyle,
} from "docx";

export const runtime = "nodejs";
export const maxDuration = 30;

function parseMarkdownToDocx(report: string, target: string, brief: string, client: string) {
  const children: Paragraph[] = [];

  // Title
  children.push(
    new Paragraph({
      text: "PANTHEON Research Intelligence Report",
      heading: HeadingLevel.TITLE,
      alignment: AlignmentType.CENTER,
    })
  );

  // Metadata
  children.push(
    new Paragraph({
      children: [
        new TextRun({ text: "Target demographic: ", bold: true }),
        new TextRun({ text: target }),
      ],
      spacing: { before: 200 },
    })
  );
  if (client) {
    children.push(
      new Paragraph({
        children: [
          new TextRun({ text: "Client: ", bold: true }),
          new TextRun({ text: client }),
        ],
      })
    );
  }
  children.push(
    new Paragraph({
      children: [
        new TextRun({ text: "Generated: ", bold: true }),
        new TextRun({ text: new Date().toLocaleString() }),
      ],
    })
  );
  children.push(
    new Paragraph({
      children: [
        new TextRun({ text: "Brief: ", bold: true }),
        new TextRun({ text: brief }),
      ],
      spacing: { after: 300 },
    })
  );

  // Divider
  children.push(
    new Paragraph({
      text: "─".repeat(50),
      spacing: { before: 200, after: 200 },
    })
  );

  // Parse report lines
  for (const rawLine of report.split("\n")) {
    const line = rawLine.trimEnd();

    if (!line.trim()) {
      children.push(new Paragraph({ text: "", spacing: { before: 80 } }));
      continue;
    }

    if (line.startsWith("### ")) {
      children.push(new Paragraph({ text: line.slice(4).trim(), heading: HeadingLevel.HEADING_3 }));
      continue;
    }
    if (line.startsWith("## ")) {
      children.push(new Paragraph({ text: line.slice(3).trim(), heading: HeadingLevel.HEADING_2 }));
      continue;
    }
    if (line.startsWith("# ")) {
      children.push(new Paragraph({ text: line.slice(2).trim(), heading: HeadingLevel.HEADING_1 }));
      continue;
    }
    if (/^[-=─]{3,}\s*$/.test(line)) {
      children.push(new Paragraph({ text: "─".repeat(50), spacing: { before: 120, after: 120 } }));
      continue;
    }

    // Inline bold parsing
    const parts = line.split(/(\*\*[^*]+\*\*)/g);
    const runs = parts.map((part) => {
      if (part.startsWith("**") && part.endsWith("**")) {
        return new TextRun({ text: part.slice(2, -2), bold: true });
      }
      return new TextRun({ text: part });
    });

    children.push(new Paragraph({ children: runs, spacing: { before: 60, after: 60 } }));
  }

  return new Document({
    sections: [{ children }],
  });
}

export async function POST(req: NextRequest) {
  try {
    const { report, target, client, brief } = await req.json();
    if (!report) return NextResponse.json({ error: "No report provided" }, { status: 400 });

    const doc = parseMarkdownToDocx(report, target || "", brief || "", client || "");
    const buffer = await Packer.toBuffer(doc);

    const slug = ((client || target || "report") as string)
      .replace(/[^\w]/g, "_")
      .slice(0, 40);
    const filename = `PANTHEON_Report_${slug}.docx`;

    return new NextResponse(buffer as unknown as BodyInit, {
      status: 200,
      headers: {
        "Content-Type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "Content-Disposition": `attachment; filename="${filename}"`,
      },
    });
  } catch (err: unknown) {
    console.error("[docx download]", err);
    return NextResponse.json(
      { error: err instanceof Error ? err.message : "Failed to generate docx" },
      { status: 500 }
    );
  }
}
