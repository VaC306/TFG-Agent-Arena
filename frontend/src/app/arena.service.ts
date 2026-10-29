import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom, timeout } from 'rxjs';

export type PresetId = 'simulated' | 'ollama' | 'codex';
export interface OpenaiSession {linked:boolean;plan?:string;models?:{name:string;display_name:string}[]}
export type Status = 'queued' | 'running' | 'completed' | 'succeeded' | 'failed' | 'timeout' | 'limit' | 'cancelled' | 'interrupted';
export interface Agent { model: string; system_prompt: string; temperature?:number; seed?:number; num_ctx?:number; limits?:{max_output_tokens:number; timeout_s:number} }
export type EvaluationMode = 'exact_match' | 'json_match' | 'none';
export interface InferenceSettings { temperature:number; seed:number; num_ctx:number; max_output_tokens:number; timeout_s:number; warmup:'none'|'per_run';order_policy:'random'|'balanced';latency_study:boolean;planned_attempts:number }
export const defaultSettings = (): InferenceSettings => ({temperature:0, seed:42, num_ctx:16384, max_output_tokens:4096, timeout_s:120, warmup:'none',order_policy:'random',latency_study:false,planned_attempts:2});
export interface ProtocolReport {
  version:string; evaluator_version:string; comparison_scope:string; inputs_shared:boolean; prompts_equal:boolean;
  evaluations:string[]; warnings:string[];
  models:Record<string,{digest:string|null; server_version:string|null; quantization:string|null; verified:boolean}>;
  branches:Record<string,{evaluated:number; correct:number; execution_errors:number; cancelled:number; mean_answer_s:number|null}>;
}
export interface Config {
  name: string; adapter: PresetId; split: string; repetitions: number;
  agents: { A: Agent; B: Agent };
  comparison?: 'same_model' | 'different_models';latency_study?:boolean;planned_attempts?:number;order_policy?:string;
}
export interface Preset { id: PresetId; config: Config }
export interface ExperimentSummary {
  id: string; name: string; adapter: PresetId; split: string;
  total: number; completed: number; created_at: number;
}
export interface Result {
  first_visible_token_s?:number;
  success: boolean | null; format_ok?: boolean | null; agent_s?: number; queue_s?: number;
  input_tokens?: number | null; output_tokens?: number | null; usage_complete?: boolean;
  tool_calls?: number; tool_errors?: number; server_tps?: number | null;
  error?: string; answer?: string; reason?: string;
  preparation_s?:number; task_s?:number|null; failure_phase?:string|null;
  warmup?:{policy:string;status:string;duration_s?:number;usage?:unknown};
  resources?:{samples:number;peak_worker_rss_bytes:number|null;min_host_ram_available_bytes:number|null;peak_host_gpu_used_bytes:unknown;worker_cpu_delta_s:number|null;max_gap_s:number|null;sampling_overhead_s:number;unavailable:string[]};
}
export interface Run {
  id: string; task_id: string; branch: 'A' | 'B'; repetition: number;
  status: Status; result: Result | null;
}
export interface ResultSummary { total:number; finished:number; evaluated:number; planned_evaluable:number; correct:number; incorrect:number; invalid_format:number; execution_errors:number; cancelled:number; unscored:number; pending:number; mean_answer_s:number|null; timed_answers:number }
export interface ModelMetrics {
  p95_answer_s:number|null; latency_samples:number; mean_server_tps:number|null; speed_samples:number;
  usage_samples:number; input_tokens:number|null; output_tokens:number|null;
  total_run_s:number|null; duration_samples:number;
}
export interface ModelResult { metrics?:ModelMetrics; external_deviation?:boolean; annotations?:OperatorAnnotation[]; comparison_conditions?:Record<string,unknown>; id:string; model:string; adapter:PresetId; digest:string|null; verified:boolean; kind:string; experiment_id:string; experiment_name:string; branch:string; updated_at:number; split:string; repetitions:number; summary:ResultSummary; cohort_key:string; conditions:{system_prompt:string; temperature:number; seed:number; num_ctx:number; limits:{max_output_tokens:number; timeout_s:number}; server_version:string|null; quantization:string|null; data_sha256:string; evaluator_versions:string[];warmup_policy?:string;resource_sample_interval_s?:number|null} }
export interface SavedTask { id: string; input: string; expected_answer?: string | null; evaluation?:EvaluationMode; criteria?:{total_cents:number; order_ids:string[]}; attachments?: {name: string; size: number; sha256: string}[] }
export interface ExperimentDetail { campaign?:{id:string;sequence:number}|null; snapshot: { config: Config; tasks?: SavedTask[]; branch_tasks?: Record<string, SavedTask> | null; conditions?: {inputs_shared?: boolean}; data_sha256?:string; git_commit?:string }; runs: Run[]; protocol?:ProtocolReport; overviews:Record<'A'|'B',ResultSummary> }
export interface CampaignSummary { id:string; name:string; created_at:number; source_id:string; adapter:PresetId; split:string; attempts:number; pending:number }
export interface OperatorAnnotation { id:string; experiment_id:string;created_at:number;kind:'observation'|'deviation';text:string }
export interface WorkerStatus { observed_at:number;state:'active'|'unobserved'|'no_recent_signal';active_workers:number;busy_workers:number;last_signal_at:number|null;stale_after_s:number;queued:number;running:number;oldest_pending_age_s:number|null }
export interface CampaignAttempt { annotations:OperatorAnnotation[]; experiment_id:string; sequence:number; request_id:string|null; created_at:number; complete:boolean; compatible:boolean; warnings:string[]; overviews:Record<'A'|'B',ResultSummary> }
export interface TaskSeries { sequence:number; experiment_id:string; summary:ResultSummary; quality_rate:number|null; outcomes:string[] }
export interface TaskBranchAnalysis { present:boolean; reference_evaluable:boolean; input_preview:string; summary:ResultSummary; quality_rate:number|null; coverage:number|null; correct_reference_rate:number|null; quality_stability:'insufficient'|'variable'|'always_correct'|'always_incorrect'; between_attempt_changes:number; between_attempt_comparisons:number; series:TaskSeries[] }
export interface TaskAnalysis { task_id:string; branches:Record<'A'|'B',TaskBranchAnalysis> }
export interface PairedAnalysis { inputs_shared:boolean; scope:string; planned_pairs:number; evaluated_pairs:number; missing_pairs:number; both_correct:number; A_only_correct:number; B_only_correct:number; both_incorrect:number; task_count:number; mean_B_minus_A:number|null; interval:{low:number;high:number}|null; interval_unavailable_reasons:string[]; method:{name:string; confidence_level:number;resamples:number;seed:number;unit:string;min_tasks:number;min_attempts:number;input_sha256:string;numpy_version:string;scipy_version:string}; note:string }
export interface LatencyAnalysis { version:string;scope:string;plan:{planned_attempts:number;question:string;endpoint:string}|null;included_attempts:number;excluded_attempts:number;task_count:number;planned_pairs:number;timed_pairs:number;missing_pairs:number;incorrect_pairs:number;unscored_pairs:number;mean_B_minus_A_s:number|null;by_order:Record<string,{timed_pairs:number;mean_B_minus_A_s:number|null}>;tasks:{task_id:string;planned_pairs:number;timed_pairs:number;mean_B_minus_A_s:number|null;A_first_pairs:number;B_first_pairs:number}[];interval:{low_s:number;high_s:number}|null;interval_unavailable_reasons:string[];method:unknown;note:string }
export interface CampaignAnalysis { latency:LatencyAnalysis; version:string; included_attempts:{sequence:number;experiment_id:string}[]; excluded_attempts:{sequence:number;experiment_id:string;reasons:string[]}[]; tasks:TaskAnalysis[]; paired:PairedAnalysis; note:string }
export interface CampaignDetail { id:string; name:string; source_id:string; created_at:number; design_sha256:string; design:{config:Config; tasks:SavedTask[]; branch_tasks:Record<string,SavedTask>|null; conditions:unknown; protocol:unknown}; expected_models:Record<string,{digest:string;server_version:string;quantization:string}>; case_count:number; attempts:CampaignAttempt[]; pending:number; note:string; analysis:CampaignAnalysis }
export interface PromptTemplate { id: string; name: string; text: string }
export interface Upload { name: string; data_base64: string; preview: string; image: boolean; size: number }
export interface InputData { text: string; files: Upload[]; expected_answer: string }
export interface ComparisonBody {
  request_id?:string;
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
export interface LibraryEntry {id:string;kind:'dataset'|'prompt';name:string;version:number;sha256:string;content:{text:string|null;cases:DatasetCase[]|null;tags:string[]}}
export interface Preflight {ready:boolean;errors:string[];warnings:string[];planned_runs:number}
export interface BlindPair {id:string;task_id:string;input:string;left:string;right:string;rubric:string}
export interface ReviewResult {task_id:string;repetition:number;mapping:Record<string,string>;score:unknown}
export interface BaselineReport {compatible:boolean;reasons:string[];note:string;cases:{task_id:string;branch:string;repetition:number;before:string;after:string;change:string;before_answer:string|null;after_answer:string|null}[]}
export const terminal = (run: Run) => !['queued', 'running'].includes(run.status);

@Injectable({ providedIn: 'root' })
export class ArenaService {
  private http = inject(HttpClient);
  private get<T>(path: string) { return firstValueFrom(this.http.get<T>('/api' + path).pipe(timeout(15000))); }
  openaiStatus() { return this.get<OpenaiSession>('/openai/status'); }
  openaiConnect() { return firstValueFrom(this.http.post<OpenaiSession>('/api/openai/connect',{}).pipe(timeout(30000))); }
  openaiDisconnect() { return firstValueFrom(this.http.post<OpenaiSession>('/api/openai/disconnect',{}).pipe(timeout(15000))); }
  openaiModels() { return firstValueFrom(this.http.get<OpenaiSession>('/api/openai/models').pipe(timeout(30000))); }
  experiments(options?:{offset?:number;search?:string;adapter?:string;status?:string;since?:string;until?:string}) {
    const query = new URLSearchParams();
    for (const [key,value] of Object.entries(options ?? {})) if (value !== undefined && value !== '') query.set(key,String(value));
    return this.get<ExperimentSummary[]>('/experiments'+(query.size?'?'+query:''));
  }
  progress(id:string) { return this.get<Pick<ExperimentDetail,'runs'|'overviews'|'protocol'|'campaign'>>(`/experiments/${encodeURIComponent(id)}/progress`); }
  recoverWorker() { return firstValueFrom(this.http.post<{recovered:number}>('/api/worker/recover',{workers_stopped:true}).pipe(timeout(15000))); }
  library() { return this.get<LibraryEntry[]>('/library'); }
  saveLibrary(body:{kind:'dataset'|'prompt';name:string;text?:string;cases?:DatasetCase[];tags?:string[]}) { return firstValueFrom(this.http.post<{id:string;version:number}>('/api/library',body).pipe(timeout(30000))); }
  preflight(body:ComparisonBody) { return firstValueFrom(this.http.post<Preflight>('/api/comparisons/preflight',body).pipe(timeout(90000))); }
  batch(comparisons:ComparisonBody[]) { return firstValueFrom(this.http.post<{ids:string[]}>('/api/comparisons/batch',{comparisons}).pipe(timeout(120000))); }
  attachmentPreview(body:{name:string;data_base64:string}) { return firstValueFrom(this.http.post<{text:string;sha256:string}>('/api/attachments/preview',body).pipe(timeout(20000))); }
  startReview(id:string,task_id:string,repetition:number) { return firstValueFrom(this.http.post<BlindPair>(`/api/experiments/${encodeURIComponent(id)}/reviews`,{task_id,repetition}).pipe(timeout(15000))); }
  scoreReview(id:string,body:unknown) { return firstValueFrom(this.http.post<ReviewResult>(`/api/reviews/${encodeURIComponent(id)}`,body).pipe(timeout(15000))); }
  reviews(id:string) { return this.get<ReviewResult[]>(`/experiments/${encodeURIComponent(id)}/reviews`); }
  baseline(id:string,baseline:string) { return this.get<BaselineReport>(`/experiments/${encodeURIComponent(id)}/baseline/${encodeURIComponent(baseline)}`); }
  modelResults() { return this.get<{entries:ModelResult[]}>('/model-results'); }
  workerStatus() { return this.get<WorkerStatus>('/worker/status'); }
  annotateAttempt(id:string,experiment_id:string,body:{request_id:string;kind:string;text:string}) {
    return firstValueFrom(this.http.post<{id:string}>(`/api/campaigns/${encodeURIComponent(id)}/attempts/${encodeURIComponent(experiment_id)}/annotations`,body).pipe(timeout(30000)));
  }
  campaigns() { return this.get<CampaignSummary[]>('/campaigns'); }
  campaign(id:string) { return this.get<CampaignDetail>(`/campaigns/${encodeURIComponent(id)}`); }
  createCampaign(experiment_id:string,name:string) {
    return firstValueFrom(this.http.post<{id:string}>('/api/campaigns',{experiment_id,name}).pipe(timeout(30000)));
  }
  repeatCampaign(id:string,request_id:string) {
    return firstValueFrom(this.http.post<{id:string}>(`/api/campaigns/${encodeURIComponent(id)}/attempts`,{request_id}).pipe(timeout(30000)));
  }
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
  detail(id: string) { return this.get<ExperimentDetail>(`/experiments/${encodeURIComponent(id)}?compact=true`); }
  events(id: string) { return this.get<ArenaEvent[]>(`/runs/${encodeURIComponent(id)}/events`); }
  create(config: PresetId,request_id?:string) {
    return firstValueFrom(this.http.post<{id: string}>('/api/experiments', { config,request_id }).pipe(timeout(30000)));
  }
  cancel(id: string) {
    return firstValueFrom(this.http.post(`/api/runs/${encodeURIComponent(id)}/cancel`, {}).pipe(timeout(15000)));
  }
}
