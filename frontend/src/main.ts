import { provideZonelessChangeDetection } from '@angular/core';
import { bootstrapApplication } from '@angular/platform-browser';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { RootComponent } from './app/root.component';
import { sessionInterceptor } from './app/auth.service';

bootstrapApplication(RootComponent, {
  providers: [provideHttpClient(withInterceptors([sessionInterceptor])), provideZonelessChangeDetection()],
}).catch(console.error);
