import { Component, computed, input, signal } from '@angular/core';
import { DecimalPipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ModelResult } from './arena.service';
import { CostRate, modelComparisonCharts, rateKey } from './model-comparison-data';

@Component({selector:'arena-model-comparison',standalone:true,imports:[DecimalPipe,FormsModule],
  templateUrl:'./model-comparison.component.html',styleUrl:'./model-comparison.component.css'})
export class ModelComparisonComponent {
  entries=input.required<ModelResult[]>();
  selected=input<ModelResult[]>([]);
  stale=input(false);
  selectionOnly=signal(false);
  rates=signal<Record<string,CostRate>>({});
  shown=computed(()=>this.selectionOnly()?this.selected():this.entries());
  charts=computed(()=>modelComparisonCharts(this.shown(),this.rates()));
  pricedModels=computed(()=>[...new Map(this.shown().filter(e=>e.adapter!=='simulated').map(e=>[rateKey(e),e])).values()]);
  compatible=computed(()=>{
    const rows=this.shown();
    return rows.length>=2 && rows.every(e=>e.adapter==='ollama' && e.verified && !e.external_deviation && e.cohort_key===rows[0].cohort_key)
      && new Set(rows.map(e=>e.digest)).size===rows.length;
  });
  rate(entry:ModelResult):CostRate { return this.rates()[rateKey(entry)]??{basis:entry.adapter==='ollama'?'hour':'tokens',input:null,output:null,hour:null}; }
  setBasis(entry:ModelResult,basis:'tokens'|'hour') { this.rates.update(r=>({...r,[rateKey(entry)]:{...this.rate(entry),basis}})); }
  setRate(entry:ModelResult,field:'input'|'output'|'hour',raw:unknown) {
    const value=typeof raw==='number' && Number.isFinite(raw) && raw>=0?raw:null;
    this.rates.update(r=>({...r,[rateKey(entry)]:{...this.rate(entry),[field]:value}}));
  }
}
