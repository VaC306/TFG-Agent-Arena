import { Component, DestroyRef, EventEmitter, inject, Output, signal } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { ArenaService } from './arena.service';
import { AuthService } from './auth.service';

@Component({selector:'arena-openai-connection',standalone:true,template:`
  <section aria-label="Conexión ChatGPT" class="connection-row">
    <div><h3>ChatGPT · suscripción</h3>
      <p class="hint">Usa la sesión del cliente oficial Codex de este equipo. Consume sus límites compartidos y, según tu cuenta, créditos adicionales. No requiere API key.</p>
      <p class="hint">La sesión de ChatGPT pertenece al usuario de Windows. Vincúlala solo si tienes permiso para usarla. Arena guarda la vinculación para tu cuenta local, sin copiar credenciales.</p>
      @if (linked()) {
        <p role="status">Sesión vinculada a esta cuenta de Arena.</p>
        <button type="button" class="secondary" [disabled]="busy()" (click)="act(false)">Desvincular de Arena</button>
        <p class="hint">Desvincular detiene las ejecuciones activas de esta conexión; conserva resultados y no cierra la sesión del cliente Codex.</p>
      }
      <button type="button" class="secondary" [disabled]="busy()" (click)="act(true)">{{ busy() ? 'Comprobando…' : linked() ? 'Volver a vincular sesión actual' : 'Usar sesión de ChatGPT de este equipo' }}</button>
      <details><summary>Preparar el cliente oficial</summary><p>Instala Codex e inicia sesión con <code>codex login</code> desde una terminal. Elige ChatGPT y completa el acceso en el navegador oficial. Después vuelve aquí y pulsa Usar sesión. Arena no gestiona contraseñas ni inicia sesión con API keys.</p><a href="https://developers.openai.com/codex/cli" target="_blank" rel="noopener noreferrer">Instalación oficial de Codex ↗</a></details>
      @if (message()) { <p class="hint" role="status">{{ message() }}</p> }
      @if (error()) { <p class="alert error" role="alert">{{ error() }}</p> }
    </div>
  </section>
`})
export class OpenaiConnectionComponent {
  private api = inject(ArenaService);
  private auth = inject(AuthService);
  private owner = this.auth.user()?.id;
  private destroyed = false;
  linked = signal(false);
  busy = signal(true);
  message = signal('');
  error = signal('');
  @Output() changed = new EventEmitter<void>();
  private current() { return !this.destroyed && this.auth.user()?.id === this.owner; }
  constructor() {
    inject(DestroyRef).onDestroy(()=>this.destroyed=true);
    void this.api.openaiStatus().then(r=>{if(this.current()) this.linked.set(r.linked);})
      .catch(()=>{if(this.current()) this.error.set('No se pudo consultar la vinculación. Reintenta con el botón.');})
      .finally(()=>{if(this.current()) this.busy.set(false);});
  }
  async act(connect:boolean) {
    if (this.busy()) return;
    this.busy.set(true); this.error.set(''); this.message.set('');
    try {
      const result = await (connect ? this.api.openaiConnect() : this.api.openaiDisconnect());
      if (!this.current()) return;
      this.linked.set(result.linked);
      this.message.set(connect ? 'ChatGPT conectado. El catálogo no garantiza acceso a cada modelo; la ejecución lo comprobará.' : 'Vinculación retirada de Arena.');
      this.changed.emit();
    } catch (error) {
      if (this.current()) this.error.set(error instanceof HttpErrorResponse && typeof error.error?.detail === 'string' ? error.error.detail : 'No se pudo completar la conexión. Comprueba Codex e inténtalo de nuevo.');
    } finally { if(this.current()) this.busy.set(false); }
  }
}
