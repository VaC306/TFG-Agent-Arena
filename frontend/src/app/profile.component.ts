import { Component, EventEmitter, inject, Output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AuthService, accountError } from './auth.service';

@Component({selector:'arena-profile', standalone:true, imports:[FormsModule], template:`
  <section class="profile-view view-enter" aria-labelledby="profile-title">
    <div class="section-header"><div><p class="eyebrow">Tu espacio</p><h1 id="profile-title">Perfil</h1></div><button class="secondary" (click)="closed.emit()">Volver</button></div>
    <div class="profile-columns"><form #form="ngForm" (ngSubmit)="save()" class="profile-form">
      <h2>{{ auth.user()?.display_name }}</h2><p class="hint">{{ '@' + auth.user()?.username }} · Cuenta local</p>
      <label for="profile-name">Nombre visible</label><input id="profile-name" name="name" [(ngModel)]="name" required maxlength="80">
      <button class="primary" [disabled]="busy() || form.invalid">Guardar nombre</button>
      <p class="hint">Tus selecciones de modelos, prompts y parámetros se guardan automáticamente. Tus experimentos pertenecen a esta cuenta.</p>
      <button type="button" class="text-button" [disabled]="busy()" (click)="logout()">Cerrar sesión</button>
      @if (message()) { <p class="hint" role="status">{{ message() }}</p> }
      @if (error()) { <p class="alert error" role="alert">{{ error() }}</p> }
    </form><section class="connections"><h2>Conexiones</h2><p class="hint">Aquí reunirás tus proveedores de modelos.</p>
      <div class="connection-row"><div><h3>Ollama</h3><p class="hint">Modelos instalados en esta máquina</p></div><span class="tag">Local</span></div>
      <div class="connection-row"><div><h3>ChatGPT</h3><p class="hint">Vinculación por cuenta en una próxima fase</p></div><span class="tag">Próximamente</span></div>
      <div class="connection-row"><div><h3>Claude</h3><p class="hint">Vinculación por cuenta en una próxima fase</p></div><span class="tag">Próximamente</span></div>
      <p class="hint">Todavía no se conectan cuentas externas ni se solicitan claves de estos servicios.</p>
    </section></div>
  </section>
`})
export class ProfileComponent {
  auth = inject(AuthService);
  @Output() closed = new EventEmitter<void>();
  name = this.auth.user()?.display_name ?? '';
  busy = signal(false); error = signal(''); message = signal('');
  async save() {
    this.busy.set(true); this.error.set(''); this.message.set('');
    try { await this.auth.rename(this.name); this.message.set('Nombre guardado.'); }
    catch(error) { this.error.set(accountError(error)); }
    finally { this.busy.set(false); }
  }
  async logout() {
    this.busy.set(true); this.error.set('');
    try { await this.auth.logout(); }
    catch(error) { this.error.set(accountError(error)); }
    finally { this.busy.set(false); }
  }
}
