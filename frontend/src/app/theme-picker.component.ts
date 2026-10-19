import { Component, HostListener, signal } from '@angular/core';

type ThemePreference = 'system' | 'light' | 'dark';
declare global {
  interface Window {
    arenaTheme: { readonly preference: ThemePreference; set(value: string): boolean };
  }
}

@Component({
  selector: 'arena-theme-picker', standalone: true,
  template: `
    <label class="theme-picker">Tema
      <select aria-label="Tema" [value]="preference()" (change)="choose($event)">
        <option value="system">Sistema</option><option value="light">Claro</option><option value="dark">Oscuro</option>
      </select>
    </label>
    @if (storageFailed()) { <p class="hint" role="status">El navegador no permite guardar el tema. Se aplica durante esta visita.</p> }
  `,
})
export class ThemePickerComponent {
  preference = signal(window.arenaTheme.preference);
  storageFailed = signal(false);
  @HostListener('window:arena-theme-change') sync() { this.preference.set(window.arenaTheme.preference); }
  choose(event: Event) { this.storageFailed.set(!window.arenaTheme.set((event.target as HTMLSelectElement).value)); }
}
