import { inject, Injectable, OnDestroy, signal } from '@angular/core';
import { HttpInterceptorFn } from '@angular/common/http';
import { LoadingTracker, trackActivity } from './loading-state';

@Injectable({providedIn:'root'})
export class LoadingService implements OnDestroy {
  pending = signal(false);
  visible = signal(false);
  private tracker = new LoadingTracker((pending,visible)=>{ this.pending.set(pending); this.visible.set(visible); });
  begin() { return this.tracker.begin(); }
  ngOnDestroy() { this.tracker.dispose(); }
}

export const loadingInterceptor:HttpInterceptorFn = (request,next)=>{
  const activity = inject(LoadingService);
  return request.url.startsWith('/api/') ? trackActivity(()=>activity.begin(),()=>next(request)) : next(request);
};
