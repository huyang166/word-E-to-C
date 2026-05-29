import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import { statusLabel } from "./statusLabels";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("中文界面", () => {
  it("显示中文上传和操作按钮", () => {
    render(<App />);

    expect(screen.getByText("上传英文 Word")).toBeInTheDocument();
    expect(screen.getByText("上传中文 Word")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "解析文档" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "导出更新后的 Word" })).toBeInTheDocument();
  });

  it("把内部状态映射为中文", () => {
    expect(statusLabel.clean).toBe("未修改");
    expect(statusLabel.edited).toBe("已编辑，待同步");
    expect(statusLabel.suggested).toBe("有同步建议，待确认");
    expect(statusLabel.modified).toBe("已确认写回");
    expect(statusLabel.error).toBe("处理失败");
  });
});

it("上传解析后显示双栏段落并允许生成同步建议", async () => {
  const user = userEvent.setup();
  vi.stubGlobal(
    "fetch",
    vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          projectId: "demo",
          enFilename: "en.docx",
          zhFilename: "zh.docx",
          enBlocks: [
            {
              id: "en-00000",
              side: "en",
              kind: "paragraph",
              index: 0,
              text: "English text.",
              path: "p:0",
              mappedId: "zh-00000",
              status: "clean",
            },
          ],
          zhBlocks: [
            {
              id: "zh-00000",
              side: "zh",
              kind: "paragraph",
              index: 0,
              text: "中文文本。",
              path: "p:0",
              mappedId: "en-00000",
              status: "clean",
            },
          ],
          mappings: [{ enId: "en-00000", zhId: "zh-00000", index: 0, mapped: true }],
          warnings: [],
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          id: "en-00000",
          side: "en",
          kind: "paragraph",
          index: 0,
          text: "Updated English.",
          path: "p:0",
          mappedId: "zh-00000",
          status: "modified",
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ suggestion: "更新后的中文。" }),
      }),
  );

  render(<App />);
  const enInput = screen.getByLabelText("上传英文 Word");
  const zhInput = screen.getByLabelText("上传中文 Word");
  await user.upload(enInput, new File(["en"], "en.docx"));
  await user.upload(zhInput, new File(["zh"], "zh.docx"));
  await user.click(screen.getByRole("button", { name: "解析文档" }));

  expect(await screen.findByText("English text.")).toBeInTheDocument();
  await user.click(screen.getByText("English text."));
  await user.clear(screen.getByLabelText("英文段落内容"));
  await user.type(screen.getByLabelText("英文段落内容"), "Updated English.");
  await user.click(screen.getByRole("button", { name: "同步到中文" }));

  expect(await screen.findByDisplayValue("更新后的中文。")).toBeInTheDocument();
});

it("导出后显示更新后的 Word 下载链接", async () => {
  const user = userEvent.setup();
  vi.stubGlobal(
    "fetch",
    vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          projectId: "demo",
          enFilename: "en.docx",
          zhFilename: "zh.docx",
          enBlocks: [],
          zhBlocks: [],
          mappings: [],
          warnings: [],
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          enDownloadUrl: "/api/projects/demo/download/updated-en.docx",
          zhDownloadUrl: "/api/projects/demo/download/updated-zh.docx",
        }),
      }),
  );

  render(<App />);
  await user.upload(screen.getByLabelText("上传英文 Word"), new File(["en"], "en.docx"));
  await user.upload(screen.getByLabelText("上传中文 Word"), new File(["zh"], "zh.docx"));
  await user.click(screen.getByRole("button", { name: "解析文档" }));
  await user.click(await screen.findByRole("button", { name: "导出更新后的 Word" }));

  expect(await screen.findByRole("link", { name: "下载更新后的英文 Word" })).toHaveAttribute(
    "href",
    "/api/projects/demo/download/updated-en.docx",
  );
  expect(screen.getByRole("link", { name: "下载更新后的中文 Word" })).toHaveAttribute(
    "href",
    "/api/projects/demo/download/updated-zh.docx",
  );
});
