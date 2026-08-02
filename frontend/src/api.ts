import type {
  ConversationDetailResponse,
  ConversationResponse,
  DocumentListResponse,
  DocumentResponse,
} from "./types";

export const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
export const WS_URL = API_URL.replace(/^http/, "ws");

class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const message = body?.detail?.message ?? body?.detail ?? response.statusText;
    throw new ApiError(response.status, String(message));
  }
  if (response.status === 204) return undefined as T;
  return response.json();
}

export async function login(username: string, password: string): Promise<string> {
  const body = new URLSearchParams({ username, password });
  const response = await fetch(`${API_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  const data = await handleResponse<{ access_token: string }>(response);
  return data.access_token;
}

function authHeaders(token: string): HeadersInit {
  return { Authorization: `Bearer ${token}` };
}

export async function listDocuments(token: string): Promise<DocumentListResponse> {
  const response = await fetch(`${API_URL}/documents?limit=100`, {
    headers: authHeaders(token),
  });
  return handleResponse(response);
}

export async function ingestText(
  token: string,
  text: string,
  name: string,
): Promise<DocumentResponse> {
  const form = new FormData();
  form.append("text", text);
  form.append("name", name);
  const response = await fetch(`${API_URL}/documents`, {
    method: "POST",
    headers: authHeaders(token),
    body: form,
  });
  return handleResponse(response);
}

export async function uploadFile(
  token: string,
  file: File,
): Promise<DocumentResponse> {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch(`${API_URL}/documents`, {
    method: "POST",
    headers: authHeaders(token),
    body: form,
  });
  return handleResponse(response);
}

export async function removeDocument(token: string, id: string): Promise<void> {
  const response = await fetch(`${API_URL}/documents/${id}`, {
    method: "DELETE",
    headers: authHeaders(token),
  });
  return handleResponse(response);
}

interface ConversationListResponse {
  conversations: ConversationResponse[];
}

export async function listConversations(token: string): Promise<ConversationResponse[]> {
  const response = await fetch(`${API_URL}/conversations`, {
    headers: authHeaders(token),
  });
  const data = await handleResponse<ConversationListResponse>(response);
  return data.conversations;
}

export async function getConversation(
  token: string,
  id: string,
): Promise<ConversationDetailResponse> {
  const response = await fetch(`${API_URL}/conversations/${id}`, {
    headers: authHeaders(token),
  });
  return handleResponse(response);
}

export async function deleteConversation(token: string, id: string): Promise<void> {
  const response = await fetch(`${API_URL}/conversations/${id}`, {
    method: "DELETE",
    headers: authHeaders(token),
  });
  return handleResponse(response);
}
