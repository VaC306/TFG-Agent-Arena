import { Component, computed, input, output, signal } from '@angular/core';
import { DatePipe, DecimalPipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ModelResult } from './arena.service';
import { comparisonCsv, CostRate, modelComparisonCharts, modelProvider, orderComparisonCharts, rateKey } from './model-comparison-data';

@Component({selector:'arena-model-comparison',standalone:true,imports:[DatePipe,DecimalPipe,FormsModule],
  templateUrl:'./model-comparison.component.html',styleUrl:'./model-comparison.component.css'})
export class ModelComparisonComponent {
  entries=input.required<ModelResult[]>();
  selected=input<ModelResult[]>([]);
  stale=input(false);
  opened=output<string>();
  selectionOnly=signal(false);
  viewMode=signal<'charts'|'table'>('charts');
  order=signal('original');
  visibleKeys=signal(['quality','coverage','errors','latency','p95','speed','tokens','cost']);
  rates=signal<Record<string,CostRate>>({});
  activeDetail=signal<string|null>(null);
  shown=computed(()=>this.selectionOnly()?this.selected():this.entries());
  providers=computed(()=>[...new Map(this.shown().map(e=>{const p=modelProvider(e); return [p.key,p] as const;})).values()]);
  charts=computed(()=>orderComparisonCharts(modelComparisonCharts(this.shown(),this.rates()),this.order()));
  visibleCharts=computed(()=>this.charts().filter(c=>this.visibleKeys().includes(c.key)));
  tableRows=computed(()=>(this.charts()[0]?.rows??[]).map(row=>({...row,values:this.visibleCharts().map(c=>{const point=c.rows.find(r=>r.id===row.id);return {key:c.key,unit:c.unit,value:point?.value??null,sample:point?.sample??''};})})));
  pricedModels=computed(()=>[...new Map(this.shown().filter(e=>e.adapter!=='simulated').map(e=>[rateKey(e),e])).values()]);
  compatible=computed(()=>{
    const rows=this.shown();
    return rows.length>=2 && rows.every(e=>e.adapter==='ollama' && e.verified && !e.external_deviation && e.cohort_key===rows[0].cohort_key)
      && new Set(rows.map(e=>e.digest)).size===rows.length;
  });
  showDetail(chart:string,id:string) { this.activeDetail.set(chart+':'+id); }
  hideDetail(chart:string,id:string) { if (this.activeDetail()===chart+':'+id) this.activeDetail.set(null); }
  dismissDetail(event:Event) { this.activeDetail.set(null); event.stopPropagation(); }
  toggleMetric(key:string) {
    this.activeDetail.set(null);
    this.visibleKeys.update(keys=>keys.includes(key)?keys.length>1?keys.filter(k=>k!==key):keys:[...keys,key]);
  }
  downloadComparison() {
    const url=URL.createObjectURL(new Blob(['\uFEFF',comparisonCsv(this.visibleCharts(),this.rates())],{type:'text/csv;charset=utf-8'}));
    const link=document.createElement('a'); link.href=url; link.download='comparativa-modelos.csv';
    link.click(); setTimeout(()=>URL.revokeObjectURL(url),0);
  }
  rate(entry:ModelResult):CostRate { return this.rates()[rateKey(entry)]??{basis:entry.adapter==='ollama'?'hour':'tokens',input:null,output:null,hour:null}; }
  setBasis(entry:ModelResult,basis:'tokens'|'hour') { this.rates.update(r=>({...r,[rateKey(entry)]:{...this.rate(entry),basis}})); }
  setRate(entry:ModelResult,field:'input'|'output'|'hour',raw:unknown) {
    const value=typeof raw==='number' && Number.isFinite(raw) && raw>=0?raw:null;
    this.rates.update(r=>({...r,[rateKey(entry)]:{...this.rate(entry),[field]:value}}));
  }
}
