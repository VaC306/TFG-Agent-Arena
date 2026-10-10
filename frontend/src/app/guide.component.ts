import { afterNextRender, Component, DestroyRef, ElementRef, EventEmitter, inject, Output } from '@angular/core';

@Component({
  selector: 'arena-guide', standalone: true,
  templateUrl: './guide.component.html',
  styleUrl: './guide.component.css',
})
export class GuideComponent {
  @Output() start = new EventEmitter<void>();
  private element: ElementRef<HTMLElement> = inject(ElementRef);
  private destroyRef = inject(DestroyRef);

  constructor() {
    afterNextRender(() => {
      // Content stays readable without animation or IntersectionObserver support.
      if (matchMedia('(prefers-reduced-motion: reduce)').matches || !('IntersectionObserver' in window)) return;
      const observer = new IntersectionObserver(entries => {
        for (const entry of entries) {
          if (!entry.isIntersecting) continue;
          entry.target.classList.add('is-revealed');
          observer.unobserve(entry.target);
        }
      }, {threshold: 0.12});
      this.element.nativeElement.querySelectorAll('.guide-step').forEach(step => observer.observe(step));
      this.destroyRef.onDestroy(() => observer.disconnect());
    });
  }
}
