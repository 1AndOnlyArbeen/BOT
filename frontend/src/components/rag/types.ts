import type { RagStageData, RagStageName } from "../../types";

export interface CitationHit {
  index: number;
  label: string;
  matches?: number;
}

export interface StageState {
  status: "pending" | "running" | "done";
  data?: RagStageData;
}

export type Stages = Record<RagStageName, StageState>;

export const INITIAL_STAGES: Stages = {
  contextualize: { status: "pending" },
  analyze: { status: "pending" },
  expand: { status: "pending" },
  retrieve: { status: "pending" },
  rerank: { status: "pending" },
  assemble: { status: "pending" },
  reason: { status: "pending" },
};

export const STAGE_ORDER: RagStageName[] = [
  "contextualize",
  "analyze",
  "expand",
  "retrieve",
  "rerank",
  "assemble",
  "reason",
];

export const STAGE_LABEL: Record<RagStageName, string> = {
  contextualize: "Contextualize",
  analyze: "Analyze",
  expand: "Expand",
  retrieve: "Retrieve",
  rerank: "Rerank",
  assemble: "Assemble",
  reason: "Reason",
};
