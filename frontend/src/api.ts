import type { BlockStatus, ProjectState } from "./types";

async function readJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail ?? "请求失败，请稍后重试。");
  }
  return response.json() as Promise<T>;
}

export async function createProject(enFile: File, zhFile: File): Promise<ProjectState> {
  const form = new FormData();
  form.append("en_file", enFile);
  form.append("zh_file", zhFile);
  return readJson<ProjectState>(await fetch("/api/projects", { method: "POST", body: form }));
}

export async function requestSuggestion(input: {
  projectId: string;
  direction: "en_to_zh" | "zh_to_en";
  sourceBlockId: string;
  targetBlockId: string;
  sourceText: string;
  targetText: string;
}): Promise<string> {
  const payload = await readJson<{ suggestion: string }>(
    await fetch(`/api/projects/${input.projectId}/suggest`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input),
    }),
  );
  return payload.suggestion;
}

export async function updateBlock(input: {
  projectId: string;
  blockId: string;
  text: string;
  status: BlockStatus;
}) {
  return readJson(
    await fetch(`/api/projects/${input.projectId}/blocks/${input.blockId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: input.text, status: input.status }),
    }),
  );
}
