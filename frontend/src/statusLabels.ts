import type { BlockStatus } from "./types";

export const statusLabel: Record<BlockStatus, string> = {
  clean: "未修改",
  edited: "已编辑，待同步",
  suggested: "有同步建议，待确认",
  modified: "已确认写回",
  error: "处理失败",
};
