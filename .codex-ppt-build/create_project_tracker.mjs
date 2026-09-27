import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const workspaceDir = "/Users/maaaazin/Developer/Curriculum Projects/AQUA";
const skillDir = "/Users/maaaazin/.codex/plugins/cache/openai-primary-runtime/presentations/26.909.12148/skills/presentations";
const buildDir = path.join(workspaceDir, ".codex-ppt-build");
const outputPath = path.join(buildDir, "candidate.pptx");
const { resolvePresentationFont } = await import(pathToFileURL(path.join(skillDir, "container_tools/artifact_tool_utils.mjs")).href);
const font = resolvePresentationFont();

const p = Presentation.create({ slideSize: { width: 1280, height: 720 } });
const navy = "#102A43";
const blue = "#2878B5";
const green = "#27865B";
const amber = "#D88A24";
const pale = "#EAF2F8";
const light = "#F7F9FB";
const ink = "#1F2933";
const muted = "#52606D";
const gray = "#D9E2EC";

function box(slide, left, top, width, height, text, opts = {}) {
  const shape = slide.shapes.add({ geometry: "textbox", position: { left, top, width, height }, fill: opts.fill ?? "none", line: opts.line ?? { fill: "none", width: 0 } });
  shape.text = text;
  shape.text.style = { typeface: font, fontSize: opts.fontSize ?? 18, color: opts.color ?? ink, bold: opts.bold ?? false, autoFit: "shrink", verticalAlignment: opts.verticalAlignment ?? "middle", padding: opts.padding ?? 6, ...(opts.align ? { align: opts.align } : {}) };
  return shape;
}
function rect(slide, left, top, width, height, fill, line = { fill: fill, width: 0 }) {
  return slide.shapes.add({ geometry: "rect", position: { left, top, width, height }, fill, line });
}
function title(slide, heading, subtitle) {
  box(slide, 60, 46, 1120, 44, heading, { fontSize: 32, bold: true, color: navy, padding: 0 });
  box(slide, 60, 94, 1120, 28, subtitle, { fontSize: 15, color: muted, padding: 0 });
  rect(slide, 60, 132, 1160, 3, blue);
}

const s1 = p.slides.add();
s1.background.fill = "#FFFFFF";
title(s1, "AQUA: Current Work and Project Status", "Repository snapshot · 27 September 2026 · Completion estimate based on delivered commits and validation results");

const stats = [
  ["65%", "Estimated delivery", blue],
  ["48 / 48", "Backend tests passing", green],
  ["Pass", "Frontend lint and build", green],
  ["54", "Indexed API handlers", blue],
];
stats.forEach(([value, label, color], index) => {
  const left = 60 + index * 290;
  rect(s1, left, 160, 260, 92, pale, { fill: gray, width: 1 });
  box(s1, left + 18, 174, 224, 36, value, { fontSize: 28, bold: true, color });
  box(s1, left + 18, 212, 224, 24, label, { fontSize: 14, color: muted });
});

box(s1, 60, 286, 530, 30, "Completed capabilities", { fontSize: 21, bold: true, color: navy, padding: 0 });
const completed = [
  "Browser test generation, execution, results, and visual validation",
  "OpenAPI and Postman imports, assertions, workflows, run history",
  "Passive API security checks, ZAP entry points, evidence redaction",
  "Project ownership, URL protection, route-JWT and dependency readiness",
];
completed.forEach((item, i) => {
  rect(s1, 64, 328 + i * 57, 7, 7, green);
  box(s1, 82, 315 + i * 57, 500, 42, item, { fontSize: 16, color: ink, padding: 0 });
});

box(s1, 650, 286, 530, 30, "Next delivery focus", { fontSize: 21, bold: true, color: navy, padding: 0 });
const next = [
  ["Integration", "Run core flows with MongoDB, LM Studio, Playwright, and a test target"],
  ["Release", "Validate deployment, seed a demo project, and rehearse the walkthrough"],
  ["Polish", "Split the 783 kB frontend entry chunk and remove deprecated APIs"],
];
next.forEach(([label, item], i) => {
  const top = 324 + i * 76;
  box(s1, 650, top, 105, 24, label, { fontSize: 14, bold: true, color: blue, padding: 0 });
  box(s1, 650, top + 23, 520, 38, item, { fontSize: 16, color: ink, padding: 0 });
});
box(s1, 60, 618, 1120, 46, "Watchlist: 27 Python deprecation warnings remain. Full acceptance testing depends on live external services and a reachable target application.", { fontSize: 15, color: "#7C4A03", fill: "#FFF4DE", line: { fill: "#E6B55A", width: 1 }, padding: 12 });
s1.speakerNotes.textFrame.setText("Source: AQUA Git history and repository validation run on 27 September 2026. Backend: 48 tests passed. Frontend: lint and production build passed.");

const s2 = p.slides.add();
s2.background.fill = "#FFFFFF";
title(s2, "AQUA: Delivery Timeline", "Delivered milestones are taken from Git history. Future dates are a recommended delivery plan, not a committed schedule.");
const x0 = 420;
const chartWidth = 760;
const weeks = ["10 Jul", "21 Sep", "22 Sep", "27 Sep", "2 Oct", "7 Oct", "11 Oct"];
weeks.forEach((week, i) => {
  const x = x0 + (chartWidth / 6) * i;
  box(s2, x - 30, 153, 60, 18, week, { fontSize: 12, color: muted, align: "center", padding: 0 });
  rect(s2, x, 180, 1, 414, gray);
});
const gantt = [
  ["Foundation and architecture", 0, 0.55, green, "Done"],
  ["Core browser testing", 0.45, 1.0, green, "Done"],
  ["API testing workspace", 1.0, 1.35, green, "Done"],
  ["Security and evidence hardening", 1.1, 1.55, green, "Done"],
  ["Research and documentation", 1.55, 3.0, blue, "In progress"],
  ["End-to-end integration", 3.0, 4.0, amber, "Planned"],
  ["Deployment and demo readiness", 4.0, 5.0, amber, "Planned"],
  ["Performance and technical debt", 5.0, 6.0, amber, "Planned"],
];
gantt.forEach(([name, start, end, color, status], i) => {
  const y = 192 + i * 48;
  box(s2, 60, y - 2, 310, 26, name, { fontSize: 15, color: ink, padding: 0 });
  box(s2, 300, y - 2, 100, 26, status, { fontSize: 12, bold: true, color, align: "right", padding: 0 });
  rect(s2, x0, y + 1, chartWidth, 20, light, { fill: gray, width: 0.5 });
  rect(s2, x0 + (chartWidth / 6) * start, y + 3, (chartWidth / 6) * (end - start), 16, color);
});
rect(s2, 60, 620, 14, 14, green); box(s2, 82, 617, 72, 20, "Done", { fontSize: 13, color: muted, padding: 0 });
rect(s2, 170, 620, 14, 14, blue); box(s2, 192, 617, 90, 20, "In progress", { fontSize: 13, color: muted, padding: 0 });
rect(s2, 310, 620, 14, 14, amber); box(s2, 332, 617, 80, 20, "Planned", { fontSize: 13, color: muted, padding: 0 });
box(s2, 60, 658, 1120, 18, "Source: Git commits from 10 July to 22 September 2026 and repository scan on 27 September 2026.", { fontSize: 12, color: muted, padding: 0 });
s2.speakerNotes.textFrame.setText("Source: AQUA Git history. Delivered work is shown in green, documentation work in blue, and proposed next phase in amber.");

await fs.mkdir(path.dirname(outputPath), { recursive: true });
await (await PresentationFile.exportPptx(p)).save(outputPath);
console.log(outputPath);
