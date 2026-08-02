export type DocumentStatus = "processing" | "ready" | "failed";
export type DocumentType = "pdf" | "text";

export interface DocumentResponse {
  id: string;
  name: string;
  document_type: DocumentType;
  status: DocumentStatus;
  ingested_at: string;
  total_chunks: number | null;
  error: string | null;
}

export interface DocumentListResponse {
  documents: DocumentResponse[];
  total: number;
  page: number;
  limit: number;
}

export interface Source {
  document_id: string;
  document_name: string;
  page: number | null;
  excerpt: string;
  score: number;
}

export type Pipeline = "simple" | "agent";

export interface ConversationTurnResponse {
  pipeline: Pipeline;
  question: string;
  answer: string;
  sources: Source[];
  prompt_tokens: number;
  completion_tokens: number;
  created_at: string;
}

export interface ConversationResponse {
  id: string;
  created_at: string;
  updated_at: string;
  total_turns: number;
}

export interface ConversationDetailResponse {
  id: string;
  created_at: string;
  updated_at: string;
  turns: ConversationTurnResponse[];
}

export type ChatEvent =
  | { type: "token"; text: string }
  | { type: "complete"; answer: string; sources: Source[] }
  | { type: "error"; message: string };

export interface ChatMessage {
  id: string;
  author: "user" | "assistant";
  text: string;
  sources?: Source[];
  inProgress?: boolean;
  pipeline?: Pipeline;
}
