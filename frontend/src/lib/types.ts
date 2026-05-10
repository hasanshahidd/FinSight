export type Role = "user" | "assistant";

export interface ToolCallTrace {
  name: string;
  args: Record<string, unknown>;
  result_preview: string;
  duration_ms?: number;
}

export interface Citation {
  source?: string;
  chunk?: number;
  score?: number;
  preview?: string;
}

export interface ChatMessage {
  id: string;
  role: Role;
  content: string;
  timestamp: string;
  tool_calls?: ToolCallTrace[];
  citations?: Citation[];
  route?: string;
  rationale?: string;
  routedVia?: "n8n";
  pending?: boolean;
}

export interface ChatSession {
  id: string;
  title: string;
  createdAt: string;
  messages: ChatMessage[];
}

export interface User {
  id: string;
  email: string;
  name: string;
  persona: string;
  description: string;
}

export interface UserWithAccounts extends User {
  accounts: Account[];
}

export interface Account {
  id: string;
  name: string;
  type: "checking" | "savings" | "credit";
  starting_balance: number;
  currency: string;
}

export interface Transaction {
  id: string;
  user_id: string;
  account_id: string;
  amount: number;
  currency: string;
  category: string;
  subcategory: string;
  merchant: string;
  description: string;
  timestamp: string;
  is_recurring?: boolean;
  anomaly_score?: number;
}

export interface CategoryTotal {
  category: string;
  total: number;
  transaction_count: number;
  pct_of_total: number;
}

export interface SpendingSummary {
  period: string;
  start_date: string;
  end_date: string;
  total_spent: number;
  total_income: number;
  net: number;
  top_categories: CategoryTotal[];
  transaction_count: number;
}

export interface TrendPoint {
  label: string;
  spent: number;
  income: number;
}

export interface TrendResponse {
  period: string;
  points: TrendPoint[];
  pct_change_vs_previous: number | null;
}

export interface CostRollup {
  input_tokens: number;
  output_tokens: number;
  estimated_cost_usd: number;
  calls: number;
  model?: string;
}

export interface EvalScoreboard {
  ran_at?: string;
  total_cases?: number;
  passed?: number;
  status?: string;
  message?: string;
  scoreboard?: Record<string, number>;
}
