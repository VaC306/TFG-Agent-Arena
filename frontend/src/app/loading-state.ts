import { defer, finalize, Observable } from 'rxjs';

interface Clock {
  set(callback:()=>void, delay:number):unknown;
  clear(handle:unknown):void;
  now():number;
}
const clock:Clock = {set:(fn,delay)=>setTimeout(fn,delay),clear:handle=>clearTimeout(handle as ReturnType<typeof setTimeout>),now:()=>Date.now()};

/** Counts concurrent work and avoids flashing the global indicator for quick requests. */
export class LoadingTracker {
  private count = 0;
  private visible = false;
  private shownAt = 0;
  private showTimer:unknown;
  private hideTimer:unknown;
  private disposed = false;
  constructor(private notify:(pending:boolean,visible:boolean)=>void,private timer:Clock=clock) {}
  begin():()=>void {
    if (this.disposed) return ()=>{};
    this.timer.clear(this.hideTimer); this.hideTimer = undefined;
    this.count++;
    if (!this.visible && this.showTimer === undefined) {
      this.showTimer = this.timer.set(()=>{
        this.showTimer = undefined;
        if (this.count && !this.disposed) { this.visible = true; this.shownAt = this.timer.now(); this.emit(); }
      },180);
    }
    this.emit();
    let ended = false;
    return ()=>{
      if (ended || this.disposed) return;
      ended = true; this.count--;
      if (!this.count) {
        this.timer.clear(this.showTimer); this.showTimer = undefined;
        if (this.visible) this.hideTimer = this.timer.set(()=>{
          this.hideTimer = undefined;
          if (!this.count) { this.visible = false; this.emit(); }
        },Math.max(0,220-(this.timer.now()-this.shownAt)));
      }
      this.emit();
    };
  }
  dispose() {
    this.disposed = true;
    this.timer.clear(this.showTimer); this.timer.clear(this.hideTimer);
    this.count = 0; this.visible = false; this.emit();
  }
  private emit() { this.notify(this.count > 0,this.visible); }
}

export function trackActivity<T>(begin:()=>()=>void,work:()=>Observable<T>):Observable<T> {
  return defer(()=>{
    const end = begin();
    return defer(work).pipe(finalize(end));
  });
}
