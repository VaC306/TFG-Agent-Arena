import { DEMO_MODE } from './runtime-mode';
import { inject, Injectable, signal } from '@angular/core';
import { HttpClient, HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { firstValueFrom, tap, timeout } from 'rxjs';
import { EvaluationMode, InferenceSettings } from './arena.service';

export interface Preferences {
  name: string; adapter: 'simulated' | 'ollama' | 'codex'; mode: 'same_model' | 'different_models';
  source: 'manual' | 'dataset'; repetitions: number; modelA: string; modelB: string;
  promptA: {template: string; text: string}; promptB: {template: string; text: string};
  evaluation?:EvaluationMode; settings?:InferenceSettings;
  split?:'dev'|'eval';
  independentInputs?:boolean;
}
export interface User { id: string; username: string; display_name: string; preferences: Preferences }

@Injectable({providedIn: 'root'})
export class AuthService {
  private http = inject(HttpClient);
  user = signal<User | null>(null);
  ready = signal(false);
  hasUsers = signal(true);
  initError = signal('');
  sessionEpoch = 0;

  async initialize() {
    if (DEMO_MODE) throw new Error('El acceso lo gestiona Sites. La demo no modifica cuentas ni preferencias.');
    const epoch = ++this.sessionEpoch;
    this.initError.set('');
    try {
      const result = await firstValueFrom(this.http.get<{user: User | null; has_users: boolean}>('/api/auth/session').pipe(timeout(15000)));
      if (epoch === this.sessionEpoch) { this.user.set(result.user); this.hasUsers.set(result.has_users); }
    } catch { this.initError.set('No se pudo conectar con la API. Comprueba que esté iniciada.'); }
    finally { this.ready.set(true); }
  }

  async authenticate(register: boolean, username: string, password: string, display_name: string) {
    if (DEMO_MODE) throw new Error('El acceso lo gestiona Sites. La demo no modifica cuentas ni preferencias.');
    const epoch = ++this.sessionEpoch;
    const result = await firstValueFrom(this.http.post<{user: User}>('/api/auth/' + (register ? 'register' : 'login'),
      {username, password, ...(register ? {display_name} : {})}).pipe(timeout(15000)));
    if (epoch === this.sessionEpoch) { this.user.set(result.user); this.hasUsers.set(true); }
  }

  async logout() {
    if (DEMO_MODE) throw new Error('El acceso lo gestiona Sites. La demo no modifica cuentas ni preferencias.');
    const epoch = ++this.sessionEpoch;
    await firstValueFrom(this.http.post('/api/auth/logout', {}).pipe(timeout(15000)));
    if (epoch === this.sessionEpoch) {
      // Explicit logout ends this account's selection, not its saved drafts.
      // Ordinary login and expired-session recovery still support deep links.
      window.history.replaceState(null, '', '#/compose');
      this.user.set(null);
    }
  }

  async savePreferences(preferences: Preferences) {
    if (DEMO_MODE) throw new Error('El acceso lo gestiona Sites. La demo no modifica cuentas ni preferencias.');
    const user = this.user();
    if (!user) return;
    const saved = await firstValueFrom(this.http.put<Preferences>('/api/profile/preferences', preferences).pipe(timeout(15000)));
    if (this.user()?.id === user.id) this.user.update(current => current ? {...current, preferences:saved} : null);
  }

  async rename(display_name: string) {
    if (DEMO_MODE) throw new Error('El acceso lo gestiona Sites. La demo no modifica cuentas ni preferencias.');
    const user = this.user();
    const saved = await firstValueFrom(this.http.patch<{display_name: string}>('/api/profile', {display_name}).pipe(timeout(15000)));
    if (this.user()?.id === user?.id) this.user.update(current => current ? {...current, ...saved} : null);
  }
}

export const sessionInterceptor: HttpInterceptorFn = (request, next) => {
  if (DEMO_MODE && /(^|\/)api(\/|$)/.test(request.url)) throw new Error('La demo no dispone de API. Utiliza los resultados guardados.');
  const auth = inject(AuthService);
  if (!request.url.startsWith('/api/')) return next(request);
  const epoch = auth.sessionEpoch;
  return next(request.clone({setHeaders:{'X-Arena-Request':'1'}})).pipe(tap({error: error => {
    if (error instanceof HttpErrorResponse && error.status === 401 && epoch === auth.sessionEpoch) auth.user.set(null);
  }}));
};

export function accountError(error: unknown) {
  const detail = error instanceof HttpErrorResponse ? error.error?.detail : null;
  return typeof detail === 'string' ? detail : Array.isArray(detail) ? 'Revisa los campos y sus límites. Hay datos no válidos.' : 'No se pudo confirmar la operación. Comprueba la conexión y actualiza los datos antes de reintentar.';
}
