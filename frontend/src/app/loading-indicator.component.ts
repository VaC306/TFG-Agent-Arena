import { Component, input } from '@angular/core';

@Component({selector:'arena-loading',standalone:true,template:`
  <span class="loading-state" role="status" aria-live="polite" aria-atomic="true">
    <span class="loading-spinner" aria-hidden="true"></span><span>{{ label() }}</span>
  </span>
`})
export class LoadingIndicatorComponent { label = input('Cargando…'); }
