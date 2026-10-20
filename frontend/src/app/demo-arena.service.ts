import { Injectable } from '@angular/core';
import { ArenaService, ExperimentDetail, ExperimentSummary, ModelResult, CampaignSummary, CampaignDetail, WorkerStatus, Preset, PromptTemplate, ArenaEvent } from './arena.service';

interface Catalog { experiments:ExperimentSummary[]; details:Record<string,ExperimentDetail>; entries:ModelResult[]; campaigns:CampaignSummary[] }
@Injectable()
export class DemoArenaService extends ArenaService {
  private cached: Promise<Catalog> | null = null;
  private catalog() {
    return this.cached ??= fetch(new URL('demo/catalog.json', document.baseURI))
      .then(response => { if (!response.ok) throw new Error('No se pudieron cargar los resultados guardados.'); return response.json() as Promise<Catalog>; })
      .catch(error => { this.cached = null; throw error; });
  }
  override async openaiStatus() { return {linked:false}; }
  override async openaiConnect():Promise<never> { return this.readonlyError(); }
  override async openaiDisconnect():Promise<never> { return this.readonlyError(); }
  override async openaiModels():Promise<never> { return this.readonlyError(); }
  override async experiments() { return (await this.catalog()).experiments; }
  override async detail(id:string) { const detail = (await this.catalog()).details[id]; if (!detail) throw new Error('Comparación no incluida en la selección.'); return detail; }
  override async modelResults() { return {entries:(await this.catalog()).entries}; }
  override async campaigns() { return (await this.catalog()).campaigns; }
  override async campaign(_id:string):Promise<CampaignDetail> { throw new Error('No hay campañas exportadas en esta selección.'); }
  override async events(_id:string):Promise<ArenaEvent[]> { return []; }
  override async presets():Promise<Preset[]> { return []; }
  override async prompts():Promise<PromptTemplate[]> { return []; }
  override async models() { return {available:false, models:[], error:'Demo de resultados guardados.'}; }
  override async workerStatus():Promise<WorkerStatus> { throw new Error('La demo no ejecuta un worker.'); }
  override async historyState() { return {count:(await this.experiments()).length,pending:0,revision:'readonly'}; }
  private readonlyError():never { throw new Error('Esta operación requiere la aplicación local con backend. La demo solo consulta resultados guardados.'); }
  override async annotateAttempt():Promise<{id:string}> { return this.readonlyError(); }
  override async createCampaign():Promise<{id:string}> { return this.readonlyError(); }
  override async repeatCampaign():Promise<{id:string}> { return this.readonlyError(); }
  override async clearHistory():Promise<{deleted:number}> { return this.readonlyError(); }
  override async validateDataset():Promise<never> { return this.readonlyError(); }
  override async compare():Promise<{id:string}> { return this.readonlyError(); }
  override async create():Promise<{id:string}> { return this.readonlyError(); }
  override async cancel():Promise<never> { return this.readonlyError(); }
}
