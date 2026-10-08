import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom, timeout } from 'rxjs';

export type PresetId = 'simulated' | 'ollama';
export type Status = 'queued' | 'running' | 'completed' | 'succeeded' | 'failed' | 'timeout' | 'limit' | 'cancelled' | 'interrupted';
export interface Agent { model: string; system_prompt: string }
export interface Config {
  name: string; adapter: PresetId; split: string; repetitions: number;
  agents: { A: Agent; B: Agent };
  comparison?: 'same_model' | 'different_models';
}
export interface Preset { id: PresetId; config: Config }
export interface ExperimentSummary {
  id: string; name: string; adapter: PresetId; split: string;
  total: number; completed: number; created_at: number;
}
export interface Result {
  success: boolean | null; format_ok?: boolean | null; agent_s?: number; queue_s?: number;
  input_tokens?: number; output_tokens?: number; usage_complete?: boolean;
  tool_calls?: number; tool_errors?: number; server_tps?: number | null;
  error?: string; answer?: string; reason?: string;
}
export interface Run {
  id: string; task_id: string; branch: 'A' | 'B'; repetition: number;
  status: Status; result: Result | null;
}
export interface SavedTask { input: string; attachments?: {name: string; size: number; sha256: string}[] }
export interface ExperimentDetail { snapshot: { config: Config; tasks?: SavedTask[]; branch_tasks?: Record<string, SavedTask> | null; conditions?: {inputs_shared?: boolean} }; runs: Run[] }
export interface PromptTemplate { id: string; name: string; text: string }
export interface Upload { name: string; data_base64: string; preview: string; image: boolean; size: number }
export interface InputData { text: string; files: Upload[]; expected_answer: string }
export interface ComparisonBody {
  name: string; adapter: PresetId; comparison: 'same_model' | 'different_models'; repetitions: number;
  agents: Record<string, {model: string; system_prompt: string; prompt_template: string}>;
  shared_input?: unknown; branch_inputs?: Record<string, unknown>;
}
export interface ArenaEvent { seq: number; kind: string; at: number; payload: unknown }
export const terminal = (run: Run) => !['queued', 'running'].includes(run.status);

@Injectable({ providedIn: 'root' })
export class ArenaService {
  private http = inject(HttpClient);
  private get<T>(path: string) { return firstValueFrom(this.http.get<T>('/api' + path).pipe(timeout(15000))); }
  experiments() { return this.get<ExperimentSummary[]>('/experiments'); }
  presets() { return this.get<Preset[]>('/presets'); }
  prompts() { return this.get<PromptTemplate[]>('/prompt-templates'); }
  models() { return this.get<{available: boolean; models: {name: string}[]; error: string | null}>('/models'); }
  compare(body: ComparisonBody) {
    return firstValueFrom(this.http.post<{id: string}>('/api/comparisons', body).pipe(timeout(30000)));
  }
  detail(id: string) { return this.get<ExperimentDetail>(`/experiments/${encodeURIComponent(id)}`); }
  events(id: string) { return this.get<ArenaEvent[]>(`/runs/${encodeURIComponent(id)}/events`); }
  create(config: PresetId) {
    return firstValueFrom(this.http.post<{id: string}>('/api/experiments', { config }).pipe(timeout(30000)));
  }
  cancel(id: string) {
    return firstValueFrom(this.http.post(`/api/runs/${encodeURIComponent(id)}/cancel`, {}).pipe(timeout(15000)));
  }
}
