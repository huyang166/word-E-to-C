import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import App from "./App";
import { statusLabel } from "./statusLabels";

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
