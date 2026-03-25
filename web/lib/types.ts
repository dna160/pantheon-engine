export interface PipelineConfig {
  brief: string;
  target: string;
  client: string;
  limit: number;
  groupSize: number;
  briefImages?: string[];
}

export interface PipelineResult {
  status: "success" | "error";
  report?: string;
  error?: string;
}

export type NodeStatus = "idle" | "running" | "complete" | "error";

export interface NodeState {
  id: number;
  label: string;
  phase: string;
  description: string;
  status: NodeStatus;
  detail?: string;
}

export interface CampaignEntry {
  id: string;
  timestamp: string;
  client: string;
  target: string;
  brief: string;
  elapsed: number;
  report: string;
}
