export type BlockStatus = "clean" | "edited" | "suggested" | "modified" | "error";
export type Side = "en" | "zh";

export interface TextBlock {
  id: string;
  side: Side;
  kind: "paragraph" | "heading" | "table_cell" | "unsupported";
  index: number;
  text: string;
  path: string;
  mappedId: string | null;
  status: BlockStatus;
}

export interface MappingPair {
  enId: string | null;
  zhId: string | null;
  index: number;
  mapped: boolean;
}

export interface ProjectState {
  projectId: string;
  enFilename: string;
  zhFilename: string;
  enBlocks: TextBlock[];
  zhBlocks: TextBlock[];
  mappings: MappingPair[];
  warnings: string[];
}
