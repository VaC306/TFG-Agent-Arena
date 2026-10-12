import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom, timeout } from 'rxjs';

export type PresetId = 'simulated' | 'ollama';
export type Status = 'queued' | 'running' | 'completed' | 'succeeded' | 'failed' | 'timeout' | 'limit' | 'cancelled' | 'interrupted';
export interface Agent { model: string; system_prompt: string; temperature?:number; seed?:number; num_ctx?:number; limits?:{max_output_tokens:number; timeout_s:number} }
export type EvaluationMode = 'exact_match' | 'json_match' | 'none';
export interface InferenceSettings { temperature:number; seed:number; num_ctx:number; max_output_tokens:number; timeout_s:number }
export const defaultSettings = (): InferenceSettings => ({temperature:0, seed:42, num_ctx:16384, max_output_tokens:4096, timeout_s:120});
export interface ProtocolReport {
  version:string; evaluator_version:string; comparison_scope:string; inputs_shared:boolean; prompts_equal:boolean;
  evaluations:string[]; warnings:string[];
  models:Record<string,{digest:string|null; server_version:string|null; quantization:string|null; verified:boolean}>;
  branches:Record<string,{evaluated:number; correct:number; execution_errors:number; mean_answer_s:number|null}>;
}
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
export interface ResultSummary { total:number; finished:number; evaluated:number; planned_evaluable:number; correct:number; incorrect:number; invalid_format:number; execution_errors:number; unscored:number; pending:number; mean_answer_s:number|null; timed_answers:number }
export interface ModelResult { comparison_conditions?:Record<string,unknown>; id:string; model:string; adapter:PresetId; digest:string|null; verified:boolean; kind:string; experiment_id:string; experiment_name:string; branch:string; updated_at:number; split:string; repetitions:number; summary:ResultSummary; cohort_key:string; conditions:{system_prompt:string; temperature:number; seed:number; num_ctx:number; limits:{max_output_tokens:number; timeout_s:number}; server_version:string|null; quantization:string|null; data_sha256:string; evaluator_versions:string[]} }
export interface SavedTask { id: string; input: string; expected_answer?: string | null; evaluation?:EvaluationMode; criteria?:{total_cents:number; order_ids:string[]}; attachments?: {name: string; size: number; sha256: string}[] }
export interface ExperimentDetail { snapshot: { config: Config; tasks?: SavedTask[]; branch_tasks?: Record<string, SavedTask> | null; conditions?: {inputs_shared?: boolean}; data_sha256?:string; git_commit?:string }; runs: Run[]; protocol?:ProtocolReport; overviews:Record<'A'|'B',ResultSummary> }
export interface PromptTemplate { id: string; name: string; text: string }
export interface Upload { name: string; data_base64: string; preview: string; image: boolean; size: number }
export interface InputData { text: string; files: Upload[]; expected_answer: string }
export interface ComparisonBody {
  name: string; adapter: PresetId; comparison: 'same_model' | 'different_models'; repetitions: number;
  agents: Record<string, {model: string; system_prompt: string; prompt_template: string}>;
  shared_input?: unknown; branch_inputs?: Record<string, unknown>;
  dataset?: DatasetCase[];
  evaluation?:EvaluationMode; settings?:InferenceSettings;
  split?:'dev'|'eval';
}
export interface DatasetCase { id: string; input: string; expected_answer: string | null }
export interface DatasetPreview { cases: DatasetCase[]; count: number; scored: number }
export interface ArenaEvent { seq: number; kind: string; at: number; payload: unknown }
export interface HistoryState { count: number; pending: number; revision: string }
export const terminal = (run: Run) => !['queued', 'running'].includes(run.status);

@Injectable({ providedIn: 'root' })
export class ArenaService {
  private http = inject(HttpClient);
  private get<T>(path: string) { return firstValueFrom(this.http.get<T>('/api' + path).pipe(timeout(15000))); }
  experiments() { return this.get<ExperimentSummary[]>('/experiments'); }
  modelResults() { return this.get<{entries:ModelResult[]}>('/model-results'); }
  historyState() { return this.get<HistoryState>('/profile/history'); }
  clearHistory(revision: string) {
    return firstValueFrom(this.http.delete<{deleted:number}>('/api/profile/history',
      {body:{confirmation:'clear-history', revision}}).pipe(timeout(30000)));
  }
  presets() { return this.get<Preset[]>('/presets'); }
  prompts() { return this.get<PromptTemplate[]>('/prompt-templates'); }
  models() { return this.get<{available: boolean; models: {name: string}[]; error: string | null}>('/models'); }
  validateDataset(filename: string, content: string) {
    return firstValueFrom(this.http.post<DatasetPreview>('/api/datasets/validate', {filename, content}).pipe(timeout(30000)));
  }
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
