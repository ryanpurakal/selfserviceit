// Tiny typed fetch wrapper. Vite proxies `/api/*` to the FastAPI server.

const BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "/api";

export interface Source {
  text: string;
  source: string;
  relevance: number;
  chunk_id: string;
}

export interface AnswerResponse {
  question_id: string;
  answer: string;
  sources: Source[];
  confidence: number;
  related_topics: string[];
  used_llm: boolean;
}

export interface EscalationPayload {
  question_id?: string;
  original_question: string;
  attempted_solutions: string[];
  user_feedback: string;
  user_email?: string;
}

export interface EscalationResponse {
  ticket_id: string;
  message: string;
  created_at: string;
}

export interface TopQuestion {
  query: string;
  count: number;
  deflection_rate: number;
}

export interface RecentEscalation {
  ticket_id: string;
  original_question: string;
  created_at: string;
  user_email: string | null;
}

export interface AnalyticsResponse {
  total_questions: number;
  deflected: number;
  escalated: number;
  pending: number;
  deflection_rate: number;
  average_confidence: number;
  estimated_time_saved_minutes: number;
  top_questions: TopQuestion[];
  recent_escalations: RecentEscalation[];
}

class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const data = await response.json();
      if (typeof data?.detail === "string") detail = data.detail;
    } catch {
      // ignore body parse errors
    }
    throw new ApiError(detail, response.status);
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export function askQuestion(
  query: string,
  collectionName: string = "it_docs",
): Promise<AnswerResponse> {
  return request<AnswerResponse>("/ask", {
    method: "POST",
    body: JSON.stringify({ query, collection_name: collectionName }),
  });
}

export function recordFeedback(questionId: string, deflected: boolean): Promise<{ ok: boolean }> {
  return request<{ ok: boolean }>("/feedback", {
    method: "POST",
    body: JSON.stringify({ question_id: questionId, deflected }),
  });
}

export function escalateTicket(payload: EscalationPayload): Promise<EscalationResponse> {
  return request<EscalationResponse>("/escalate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function fetchAnalytics(): Promise<AnalyticsResponse> {
  return request<AnalyticsResponse>("/analytics");
}

export { ApiError };
