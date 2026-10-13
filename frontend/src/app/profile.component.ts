import { Component, ElementRef, EventEmitter, inject, Output, signal, ViewChild } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AuthService, accountError } from './auth.service';
import { ArenaService, HistoryState } from './arena.service';
import { textError } from './validation';
import { containDialogFocus } from './info-dialog.component';
import { LoadingIndicatorComponent } from './loading-indicator.component';

@Component({selector:'arena-profile', standalone:true, imports:[FormsModule,LoadingIndicatorComponent], template:`
  <section class="profile-view view-enter" aria-labelledby="profile-title">
    <div class="section-header"><div><p class="eyebrow">Tu espacio</p><h1 id="profile-title">Perfil</h1></div><button class="secondary" (click)="closed.emit()">Volver</button></div>
    <div class="profile-columns"><form #form="ngForm" (ngSubmit)="save()" class="profile-form">
      <h2>{{ auth.user()?.display_name }}</h2><p class="hint">{{ '@' + auth.user()?.username }} · Cuenta local</p>
      <label for="profile-name">Nombre visible</label><input id="profile-name" name="name" [(ngModel)]="name" (input)="invalidName.set(false); error.set('')" [attr.aria-invalid]="invalidName() ? 'true' : null" [attr.aria-describedby]="invalidName() ? 'profile-error' : null" required maxlength="80">
      <button class="primary" [disabled]="busy()">Guardar nombre</button>
      @if (busy()) { <arena-loading label="Procesando cambios…" /> }
      <p class="hint">Tus selecciones de modelos, prompts y parámetros se guardan automáticamente. Tus experimentos pertenecen a esta cuenta.</p>
      <button type="button" class="text-button" [disabled]="busy()" (click)="logout()">Cerrar sesión</button>
      @if (message()) { <p class="hint" role="status">{{ message() }}</p> }
      @if (error()) { <p id="profile-error" class="alert error" role="alert">{{ error() }}</p> }
    </form><section class="connections"><h2>Modelos locales</h2><p class="hint">La ejecución pertenece a esta instalación.</p>
      <div class="connection-row"><div><h3>Ollama</h3><p class="hint">Modelos instalados en esta máquina</p></div><span class="tag">Local</span></div>
      <details><summary>Conexiones futuras</summary><div class="connection-row"><div><h3>ChatGPT</h3><p class="hint">Vinculación por cuenta en una próxima fase</p></div><span class="tag">Próximamente</span></div>
      <div class="connection-row"><div><h3>Claude</h3><p class="hint">Vinculación por cuenta en una próxima fase</p></div><span class="tag">Próximamente</span></div>
      <p class="hint">Todavía no se conectan cuentas externas ni se solicitan claves de estos servicios.</p></details>
    </section></div>
    <section class="profile-history" aria-labelledby="history-settings-title">
      <div><h2 id="history-settings-title">Historial</h2><p class="hint">Elimina las comparaciones, campañas y resultados de esta cuenta. Tus preferencias se conservan.</p></div>
      <button #clearTrigger type="button" class="secondary" aria-haspopup="dialog" [disabled]="clearing() || loadingHistory()" (click)="reviewHistory()">{{ loadingHistory() ? 'Consultando…' : 'Vaciar historial' }}</button>
      @if (loadingHistory()) { <arena-loading label="Consultando historial…" /> }
      @if (historyMessage()) { <p role="status" class="hint">{{ historyMessage() }}</p> }
      @if (historyError()) { <p role="alert" class="alert error">{{ historyError() }}</p> }
    </section>
    <dialog #clearDialog class="info-dialog" aria-modal="true" aria-labelledby="clear-title" aria-describedby="clear-description" (keydown)="containFocus($event)" (cancel)="cancelDialog($event)" (close)="restoreFocus()">
      <p class="eyebrow">Tu historial</p><h2 id="clear-title" tabindex="-1">¿Vaciar el historial?</h2>
      <p id="clear-description" class="dialog-description">Se eliminarán {{ history()?.count }} comparaciones, junto con sus campañas, resultados, archivos y eventos. No se pueden recuperar.</p>
      @if (history()?.pending) { <p class="alert error" role="status">Hay {{ history()?.pending }} ejecuciones pendientes. Finalízalas o cancélalas antes de vaciar el historial.</p> }
      @if (history()?.count === 0) { <p class="hint">Tu historial ya está vacío.</p> }
      @if (dialogError()) { <p class="alert error" role="alert">{{ dialogError() }}</p> }
      @if (clearing()) { <arena-loading label="Eliminando historial…" /> }
      <div class="dialog-actions"><button type="button" class="secondary" [disabled]="clearing()" (click)="clearDialog.close()">Cancelar</button><button type="button" class="primary" [disabled]="clearing() || !history()?.count || !!history()?.pending || !!dialogError()" (click)="confirmClear()">{{ clearing() ? 'Eliminando…' : 'Vaciar historial' }}</button></div>
    </dialog>
  </section>
`})
export class ProfileComponent {
  auth = inject(AuthService);
  private api = inject(ArenaService);
  @Output() closed = new EventEmitter<void>();
  @Output() historyCleared = new EventEmitter<number>();
  @ViewChild('clearDialog', {static:true}) clearDialog!: ElementRef<HTMLDialogElement>;
  @ViewChild('clearTrigger', {static:true}) clearTrigger!: ElementRef<HTMLButtonElement>;
  history = signal<HistoryState | null>(null);
  loadingHistory = signal(false); clearing = signal(false);
  historyMessage = signal(''); historyError = signal(''); dialogError = signal('');
  name = this.auth.user()?.display_name ?? '';
  busy = signal(false); error = signal(''); message = signal('');
  invalidName = signal(false);
  containFocus(event: KeyboardEvent) { containDialogFocus(this.clearDialog.nativeElement, document.getElementById('clear-title')!, event); }
  cancelDialog(event: Event) { if (this.clearing()) event.preventDefault(); }
  restoreFocus() { requestAnimationFrame(() => this.clearTrigger.nativeElement.isConnected && this.clearTrigger.nativeElement.focus()); }
  async save() {
    if (textError(this.name, 'Nombre', 80)) { this.invalidName.set(true); this.error.set(textError(this.name, 'Nombre', 80)); document.getElementById('profile-name')?.focus(); return; }
    this.busy.set(true); this.error.set(''); this.message.set('');
    try { await this.auth.rename(this.name); this.message.set('Nombre guardado.'); }
    catch(error) { this.error.set(accountError(error)); }
    finally { this.busy.set(false); }
  }
  async reviewHistory() {
    if (this.loadingHistory() || this.clearing()) return;
    this.loadingHistory.set(true); this.historyError.set(''); this.historyMessage.set(''); this.dialogError.set('');
    try {
      this.history.set(await this.api.historyState());
      this.clearDialog.nativeElement.showModal();
      document.getElementById('clear-title')?.focus();
    } catch (error) { this.historyError.set(accountError(error)); }
    finally { this.loadingHistory.set(false); }
  }
  async confirmClear() {
    const state = this.history();
    if (!state?.count || state.pending || this.clearing() || this.dialogError()) return;
    this.clearing.set(true);
    try {
      const result = await this.api.clearHistory(state.revision);
      this.clearDialog.nativeElement.close();
      this.historyMessage.set(`${result.deleted} comparaciones eliminadas.`);
      this.historyCleared.emit(result.deleted);
    } catch (error) { this.dialogError.set(accountError(error) + ' Cierra y vuelve a consultar el historial antes de reintentar.'); }
    finally { this.clearing.set(false); }
  }
  async logout() {
    this.busy.set(true); this.error.set('');
    try {
      await this.auth.logout();
      document.title = 'Iniciar sesión · Agent Arena';
      requestAnimationFrame(() => document.getElementById('auth-title')?.focus());
    }
    catch(error) { this.error.set(accountError(error)); }
    finally { this.busy.set(false); }
  }
}
