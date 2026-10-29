import { Component, Input, ViewChild, ElementRef, OnChanges, OnDestroy, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { JsonPipe } from '@angular/common';
import { ArenaService, ExperimentDetail, ExperimentSummary, BlindPair, ReviewResult, BaselineReport } from './arena.service';

@Component({selector:'arena-research-tools',standalone:true,imports:[FormsModule,JsonPipe],template:`
  <details class="panel research-tools"><summary>Revisión humana y comparación con una referencia anterior</summary>
    <p class="hint">Las valoraciones humanas se guardan aparte de la evaluación automática. La revisión oculta la correspondencia de las respuestas hasta guardar; empieza antes de leer las respuestas identificadas.</p>
    <h3>Revisión humana ciega</h3>
    <label for="review-case">Caso y repetición</label><select id="review-case" [(ngModel)]="caseKey">
      <option value="">Selecciona un par de respuestas</option>
      @for (run of reviewCases(); track run.id) { <option [value]="run.task_id+'|'+run.repetition">{{ run.task_id }} · R{{ run.repetition+1 }}</option> }
    </select>
    <button type="button" class="secondary" (click)="start()" [disabled]="busy() || !caseKey">Abrir revisión ciega</button>
    <p class="hint">{{ reviews().length }} revisiones guardadas · Rúbrica v1: corrección, claridad y utilidad, de 1 (muy baja) a 5 (muy alta).</p>
    @for (review of reviews(); track $index) { <details><summary>{{ review.task_id }} · R{{ review.repetition+1 }} · valoración humana</summary><pre>{{ review | json }}</pre></details> }
    <h3>Comparar con una referencia anterior</h3>
    <label for="baseline-id">Comparación de referencia</label><select id="baseline-id" [(ngModel)]="baselineId"><option value="">Selecciona una comparación</option>
      @for (item of history; track item.id) { @if (item.id !== experimentId) { <option [value]="item.id">{{ item.name }} · {{ item.id.slice(0,8) }}</option> } }
    </select><label for="baseline-manual">O introduce su ID</label><input id="baseline-manual" [(ngModel)]="baselineId" maxlength="100">
    <button type="button" class="secondary" (click)="compare()" [disabled]="busy() || !baselineId || baselineId===experimentId">Analizar cambios por caso</button>
    @if (baseline(); as report) {
      <p class="hint">{{ report.note }}</p>
      @if (!report.compatible) { <p class="alert">Las condiciones no permiten calcular cambios comparables.</p><ul>@for (reason of report.reasons; track $index) { <li>{{ reason }}</li> }</ul> }
      @else {
        <label for="baseline-filter">Mostrar</label><select id="baseline-filter" [(ngModel)]="baselineFilter"><option value="all">Todos</option><option value="improved">Mejoras</option><option value="regressed">Regresiones</option><option value="unscored">Sin contraste de calidad</option></select>
        <p class="hint">{{ countChanges('improved') }} mejoras · {{ countChanges('regressed') }} regresiones · {{ countChanges('unscored') }} sin contraste de calidad.</p>
        @for (item of report.cases; track $index) { @if (baselineFilter==='all' || item.change===baselineFilter) { <details><summary>{{ item.task_id }} · {{ item.branch }} · R{{ item.repetition+1 }} · {{ changeLabel(item.change) }}</summary><p>{{ item.before }} → {{ item.after }}</p><h4>Referencia anterior</h4><pre>{{ item.before_answer ?? 'Sin respuesta' }}</pre><h4>Actual</h4><pre>{{ item.after_answer ?? 'Sin respuesta' }}</pre></details> } }
      }
    }
    @if (error()) { <p class="alert error" role="alert">{{ error() }}</p> }
    @if (busy()) { <p role="status">Procesando…</p> }
  </details>
  <dialog #reviewDialog class="review-dialog" (cancel)="pair.set(null)">
    @if (pair(); as p) {
      <h2>Revisión ciega · {{ p.task_id }}</h2><h3>Entrada</h3><pre>{{ p.input }}</pre>
      <p>Valora cada criterio de 1 (muy baja) a 5 (muy alta). La corrección se juzga respecto a la solicitud; puedes indicar dudas en el comentario.</p>
      <form (ngSubmit)="save()"><div class="answer-grid">
        @for (side of sides; track side) { <section><h3>Respuesta {{ side==='left' ? '1' : '2' }}</h3><pre class="case-answer">{{ p[side] }}</pre>
          @for (criterion of criteria; track criterion) { <label [for]="side+'-'+criterion">{{ criterionLabel(criterion) }}</label><select [id]="side+'-'+criterion" [name]="side+'-'+criterion" [(ngModel)]="scores[side][criterion]" required><option [ngValue]="null">Selecciona puntuación</option>@for (value of [1,2,3,4,5]; track value) { <option [ngValue]="value">{{ value }}</option> }</select> }
        </section> }
      </div><label for="review-preference">Preferencia global</label><select id="review-preference" name="preference" [(ngModel)]="preference"><option value="tie">Empate</option><option value="left">Respuesta 1</option><option value="right">Respuesta 2</option></select>
      <label for="review-comment">Comentario</label><textarea id="review-comment" name="comment" [(ngModel)]="comment" maxlength="2000"></textarea>
      @if (reviewError()) { <p class="alert error" role="alert">{{ reviewError() }}</p> }
      <button class="primary" type="submit" [disabled]="busy() || !scoresComplete()">Guardar y revelar identidad</button>
      <button class="secondary" type="button" (click)="closeReview()" [disabled]="busy()">Cerrar sin guardar</button></form>
    }
  </dialog>
`})
export class ResearchToolsComponent implements OnChanges,OnDestroy {
  @Input({required:true}) experimentId = '';
  @Input({required:true}) detail!:ExperimentDetail;
  @Input() history:ExperimentSummary[]=[];
  @ViewChild('reviewDialog') dialog?:ElementRef<HTMLDialogElement>;
  private api=inject(ArenaService);
  private version=0;
  private destroyed=false;
  busy=signal(false); error=signal(''); reviewError=signal('');
  pair=signal<BlindPair|null>(null); reviews=signal<ReviewResult[]>([]); baseline=signal<BaselineReport|null>(null);
  caseKey=''; baselineId=''; baselineFilter='all'; comment=''; preference='tie';
  sides=['left','right'] as const; criteria=['correctness','clarity','usefulness'] as const;
  scores:Record<'left'|'right',Record<'correctness'|'clarity'|'usefulness',number|null>>={left:{correctness:null,clarity:null,usefulness:null},right:{correctness:null,clarity:null,usefulness:null}};
  private loadedId='';
  ngOnChanges() {
    if (this.loadedId===this.experimentId) return;
    this.loadedId=this.experimentId; ++this.version; this.closeReview();this.baseline.set(null);this.reviews.set([]);this.error.set('');this.busy.set(false);this.caseKey='';
    void this.loadReviews();
  }
  ngOnDestroy() {this.destroyed=true;++this.version;this.dialog?.nativeElement.close();}
  private message(error:unknown) {const detail=(error as {error?:{detail?:unknown}}).error?.detail;return typeof detail==='string'?detail:'No se pudo completar la operación. Revisa los datos y la conexión.';}
  async loadReviews() {const version=this.version;try {const rows=await this.api.reviews(this.experimentId);if (!this.destroyed && version===this.version) this.reviews.set(rows);} catch {if (!this.destroyed && version===this.version) this.error.set('No se pudieron cargar las revisiones guardadas.');}}
  reviewCases() {return this.detail?.runs.filter(r=>r.branch==='A' && ['completed','succeeded','failed'].includes(r.status) && r.result?.answer && !r.result.error && this.detail.runs.some(b=>b.branch==='B' && b.task_id===r.task_id && b.repetition===r.repetition && ['completed','succeeded','failed'].includes(b.status) && b.result?.answer && !b.result.error)) ?? [];}
  scoresComplete() {return this.sides.every(s=>this.criteria.every(c=>this.scores[s][c]!=null));}
  criterionLabel(c:string) {return ({correctness:'Corrección',clarity:'Claridad',usefulness:'Utilidad'} as Record<string,string>)[c];}
  changeLabel(c:string) {return ({improved:'Mejora',regressed:'Regresión',unchanged:'Sin cambio de calidad',unscored:'Sin contraste de calidad'} as Record<string,string>)[c];}
  countChanges(c:string) {return this.baseline()?.cases.filter(x=>x.change===c).length ?? 0;}
  closeReview() {this.dialog?.nativeElement.close();this.pair.set(null);}
  async start() {
    if (this.busy() || !this.caseKey) return;const version=this.version;this.busy.set(true);this.error.set('');
    const split=this.caseKey.lastIndexOf('|');
    try {const pair=await this.api.startReview(this.experimentId,this.caseKey.slice(0,split),Number(this.caseKey.slice(split+1)));
      if (!this.destroyed && version===this.version) {this.pair.set(pair);this.comment='';this.preference='tie';this.reviewError.set('');for(const s of this.sides) for(const c of this.criteria) this.scores[s][c]=null;this.dialog?.nativeElement.showModal();}}
    catch(error) {if(version===this.version)this.error.set(this.message(error));} finally {if(version===this.version)this.busy.set(false);}
  }
  async save() {
    const pair=this.pair();if (!pair || this.busy() || !this.scoresComplete()) return;const version=this.version;this.busy.set(true);this.reviewError.set('');
    try {await this.api.scoreReview(pair.id,{...this.scores,preference:this.preference,comment:this.comment});if (!this.destroyed && version===this.version) {this.closeReview();await this.loadReviews();}}
    catch(error) {if(version===this.version)this.reviewError.set(this.message(error));} finally {if(version===this.version)this.busy.set(false);}
  }
  async compare() {if(this.busy())return;const version=this.version;this.busy.set(true);this.error.set('');this.baseline.set(null);
    try {const report=await this.api.baseline(this.experimentId,this.baselineId);if(!this.destroyed && version===this.version)this.baseline.set(report);}
    catch(error) {if(version===this.version)this.error.set(this.message(error));} finally {if(version===this.version)this.busy.set(false);}}
}
