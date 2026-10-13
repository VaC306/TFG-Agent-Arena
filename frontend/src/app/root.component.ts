import { DEMO_MODE } from './runtime-mode';
import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AppComponent } from './app.component';
import { BrandMarkComponent } from './brand-mark.component';
import { AuthService, accountError } from './auth.service';
import { textError, passwordError } from './validation';
import { LoadingService } from './loading.service';
import { LoadingIndicatorComponent } from './loading-indicator.component';

@Component({
  selector:'arena-root', standalone:true, imports:[FormsModule, AppComponent, BrandMarkComponent, LoadingIndicatorComponent],
  template:`
    @if (activity.visible()) { <div class="global-loading" role="progressbar" aria-label="Procesando solicitudes" [attr.aria-busy]="activity.pending()"><span class="loading-spinner" aria-hidden="true"></span><span>Procesando…</span></div> }
    @if (demo) { <arena-workspace /> }
    @else if (!auth.ready()) { <main class="auth-layout" aria-busy="true"><arena-loading label="Abriendo tu espacio…" /></main> }
    @else if (auth.user()) { <arena-workspace /> }
    @else {
      <div class="auth-top"><span class="brand"><arena-brand-mark />Agent Arena</span><span class="hint">Tu laboratorio local</span></div>
      <a class="skip-link" href="#auth-title">Ir al inicio de sesión</a>
      <main class="auth-layout view-enter">
        <section class="auth-intro"><p class="eyebrow">Un espacio para tus ideas</p><h1>Experimenta.<br>Compara.<br>Quédate con<br>lo que funciona.</h1><p class="subheading">Tus modelos, tus datos y tus configuraciones.<br>Todo empieza en tu espacio.</p></section>
        <section class="auth-form" aria-labelledby="auth-title">
          @if (auth.initError()) { <p class="alert error" role="alert">{{ auth.initError() }}</p><button class="secondary" (click)="auth.initialize()">Reintentar conexión</button> }
          <p class="eyebrow">Agent Arena / Cuenta local</p><h2 id="auth-title" tabindex="-1">{{ register ? 'Crea tu espacio' : 'Qué bueno verte' }}</h2>
          <p class="hint auth-description">{{ register ? 'Guarda tus preferencias y reúne tus experimentos en un solo lugar.' : 'Entra para recuperar tus configuraciones y resultados.' }}</p>
          <form #form="ngForm" (ngSubmit)="submit()" (input)="clearValidation()">
            <fieldset [disabled]="busy()" [attr.aria-busy]="busy()">
              <legend class="sr-only">{{ register ? 'Datos de registro' : 'Datos de acceso' }}</legend>
              @if (register) { <label for="display-name">Tu nombre</label><input id="display-name" name="displayName" [(ngModel)]="displayName" maxlength="80" required autocomplete="name" [attr.aria-invalid]="invalidField() === 'display-name' ? 'true' : null" [attr.aria-describedby]="invalidField() === 'display-name' ? 'auth-error' : null"> }
              <label for="username">Usuario</label><input id="username" name="username" [(ngModel)]="username" minlength="3" maxlength="40" pattern="[A-Za-z0-9_.-]+" required autocomplete="username" autocapitalize="none" spellcheck="false" [attr.aria-describedby]="invalidField() === 'username' ? 'username-help auth-error' : 'username-help'" [attr.aria-invalid]="invalidField() === 'username' ? 'true' : null">
              <p id="username-help" class="hint">3–40 caracteres: letras, números, punto, guion o guion bajo.</p>
              <label for="password">Contraseña</label><input id="password" name="password" type="password" [(ngModel)]="password" [minlength]="register ? 10 : 1" maxlength="128" required [autocomplete]="register ? 'new-password' : 'current-password'" [attr.aria-describedby]="invalidField() === 'password' ? (register ? 'password-help auth-error' : 'auth-error') : (register ? 'password-help' : null)" [attr.aria-invalid]="invalidField() === 'password' ? 'true' : null">
              @if (register) { <p id="password-help" class="hint">Mínimo 10 caracteres. Esta cuenta pertenece a esta instalación.</p> }
              <button class="primary" type="submit" [disabled]="busy() || !!auth.initError()">@if (busy()) { <span class="loading-spinner" aria-hidden="true"></span> } {{ busy() ? 'Un momento…' : register ? 'Crear cuenta' : 'Entrar' }} @if (!busy()) { <span aria-hidden="true">↗</span> }</button>
            </fieldset>
          </form>
          @if (error()) { <p id="auth-error" class="alert error" role="alert">{{ error() }}</p> }
          <button class="text-button auth-switch" (click)="switchMode()">{{ register ? 'Ya tengo cuenta. Iniciar sesión' : '¿Primera vez? Crear una cuenta' }}</button>
          @if (register && !auth.hasUsers()) { <p class="hint">La primera cuenta conservará el historial existente de esta instalación.</p> }
        </section>
      </main>
    }
  `,
})
export class RootComponent {
  demo = DEMO_MODE;
  auth = inject(AuthService);
  activity = inject(LoadingService);
  register = false;
  username = ''; password = ''; displayName = '';
  busy = signal(false); error = signal('');
  invalidField = signal('');
  constructor() { if (!this.demo) void this.auth.initialize(); }
  clearValidation() { if (this.invalidField()) this.error.set(''); this.invalidField.set(''); }
  switchMode() {
    this.register = !this.register; this.error.set(''); this.invalidField.set(''); this.password = '';
    requestAnimationFrame(() => document.getElementById('auth-title')?.focus());
  }
  async submit() {
    if (this.busy()) return;
    const invalid = this.register && textError(this.displayName, 'Nombre', 80) ? ['display-name', textError(this.displayName, 'Nombre', 80)]
      : !/^[A-Za-z0-9_.-]{3,40}$/.test(this.username) ? ['username', 'Revisa el usuario: entre 3 y 40 letras, números, puntos o guiones.']
      : passwordError(this.password, this.register) ? ['password', passwordError(this.password, this.register)]
      : null;
    if (invalid) { this.invalidField.set(invalid[0]); this.error.set(invalid[1]); document.getElementById(invalid[0])?.focus(); return; }
    this.invalidField.set('');
    this.busy.set(true); this.error.set('');
    try { await this.auth.authenticate(this.register, this.username, this.password, this.displayName); this.password = ''; }
    catch(error) { this.error.set(accountError(error)); }
    finally { this.busy.set(false); }
  }
}
