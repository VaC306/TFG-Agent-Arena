import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AppComponent } from './app.component';
import { AuthService, accountError } from './auth.service';

@Component({
  selector:'arena-root', standalone:true, imports:[FormsModule, AppComponent],
  template:`
    @if (!auth.ready()) { <main class="auth-layout"><p class="hint" role="status">Abriendo tu espacio…</p></main> }
    @else if (auth.user()) { <arena-workspace /> }
    @else {
      <div class="auth-top"><span class="brand">a∕a &nbsp; Agent Arena</span><span class="hint">Tu laboratorio local</span></div>
      <main class="auth-layout view-enter">
        <section class="auth-intro"><p class="eyebrow">Un espacio para tus ideas</p><h1>Experimenta.<br>Compara.<br>Quédate con<br>lo que funciona.</h1><p class="subheading">Tus modelos, tus datos y tus configuraciones.<br>Todo empieza en tu espacio.</p></section>
        <section class="auth-form" aria-labelledby="auth-title">
          @if (auth.initError()) { <p class="alert error" role="alert">{{ auth.initError() }}</p><button class="secondary" (click)="auth.initialize()">Reintentar conexión</button> }
          <p class="eyebrow">Agent Arena / Cuenta local</p><h2 id="auth-title">{{ register ? 'Crea tu espacio' : 'Qué bueno verte' }}</h2>
          <p class="hint auth-description">{{ register ? 'Guarda tus preferencias y reúne tus experimentos en un solo lugar.' : 'Entra para recuperar tus configuraciones y resultados.' }}</p>
          <form #form="ngForm" (ngSubmit)="submit()">
            <fieldset [disabled]="busy()">
              @if (register) { <label for="display-name">Tu nombre</label><input id="display-name" name="displayName" [(ngModel)]="displayName" maxlength="80" required autocomplete="name"> }
              <label for="username">Usuario</label><input id="username" name="username" [(ngModel)]="username" minlength="3" maxlength="40" pattern="[A-Za-z0-9_.-]+" required autocomplete="username" autocapitalize="none" spellcheck="false">
              <label for="password">Contraseña</label><input id="password" name="password" type="password" [(ngModel)]="password" [minlength]="register ? 10 : 1" maxlength="128" required [autocomplete]="register ? 'new-password' : 'current-password'">
              @if (register) { <p class="hint">Mínimo 10 caracteres. Esta cuenta pertenece a esta instalación.</p> }
              <button class="primary" type="submit" [disabled]="form.invalid || busy() || !!auth.initError()">{{ busy() ? 'Un momento…' : register ? 'Crear cuenta' : 'Entrar' }} <span aria-hidden="true">↗</span></button>
            </fieldset>
          </form>
          @if (error()) { <p class="alert error" role="alert">{{ error() }}</p> }
          <button class="text-button auth-switch" (click)="register = !register; error.set(''); password = ''">{{ register ? 'Ya tengo cuenta. Iniciar sesión' : '¿Primera vez? Crear una cuenta' }}</button>
          @if (register && !auth.hasUsers()) { <p class="hint">La primera cuenta conservará el historial existente de esta instalación.</p> }
        </section>
      </main>
    }
  `,
})
export class RootComponent {
  auth = inject(AuthService);
  register = false;
  username = ''; password = ''; displayName = '';
  busy = signal(false); error = signal('');
  constructor() { void this.auth.initialize(); }
  async submit() {
    if (this.busy()) return;
    this.busy.set(true); this.error.set('');
    try { await this.auth.authenticate(this.register, this.username, this.password, this.displayName); this.password = ''; }
    catch(error) { this.error.set(accountError(error)); }
    finally { this.busy.set(false); }
  }
}
