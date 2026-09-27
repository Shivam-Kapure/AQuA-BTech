import path from "node:path";
import { pathToFileURL } from "node:url";

const workspaceDir = "/Users/maaaazin/Developer/Curriculum Projects/AQUA";
const skillDir = "/Users/maaaazin/.codex/plugins/cache/openai-primary-runtime/presentations/26.909.12148/skills/presentations";
const buildDir = path.join(workspaceDir, ".codex-ppt-build");
const { finalizePresentation } = await import(pathToFileURL(path.join(skillDir, "container_tools/artifact_tool_utils.mjs")).href);

const result = await finalizePresentation({
  workspaceDir,
  candidatePath: path.join(buildDir, "candidate.pptx"),
  finalPath: path.join(workspaceDir, "project-tracker", "AQUA_Project_Tracker_2026-09-27-final.pptx"),
  pythonExecutable: "/Users/maaaazin/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3",
  integrityValidatorPath: path.join(skillDir, "container_tools/inspect_presentation_package_integrity.py"),
  layoutValidatorPath: path.join(skillDir, "container_tools/inspect_presentation_layout_geometry.py"),
  layoutArgs: ["--expected-slide-size-emu", "12192000,6858000", "--validate-bullet-geometry", "--validate-heading-fit"],
  requiredNativeTableOwnerSlides: [],
  fontPolicy: { basis: "design", families: ["Helvetica Neue"] },
  verifyArtifactToolImport: true,
  receiptPath: path.join(buildDir, "AQUA_Project_Tracker.validation.json"),
});
console.log(JSON.stringify(result));
