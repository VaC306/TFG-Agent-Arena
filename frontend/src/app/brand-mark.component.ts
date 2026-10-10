import { Component } from '@angular/core';

@Component({
  selector: 'arena-brand-mark', standalone: true,
  template: `<svg viewBox="0 0 28 28" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">
    <path d="M3 5.5 9 3l6 2.5V12c0 5-6 9-6 9s-6-4-6-9Z" />
    <path d="m13.5 12.5 9-9 2 2-9 9M12 12l6 6m-3-3-6 6m-1-2 3 3" />
  </svg>`,
  styles: [':host { display: inline-flex; flex-shrink: 0; width: 28px; height: 28px; } svg { width: 100%; height: 100%; }'],
})
export class BrandMarkComponent {}
