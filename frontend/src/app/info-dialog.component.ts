import { Component, ElementRef, Input, ViewChild } from '@angular/core';

/** Native modal: the browser makes the background inert and contains keyboard focus. */
@Component({
  selector: 'arena-info', standalone: true,
  template: `
    <button #trigger type="button" class="info-trigger" aria-haspopup="dialog" (click)="open()">{{ label }}</button>
    <dialog #dialog class="info-dialog" aria-modal="true" [attr.aria-labelledby]="helpId + '-title'" (keydown)="containFocus($event)" (close)="restoreFocus()">
      <div class="dialog-heading"><p class="eyebrow">Guía de comparación</p><button type="button" class="secondary" (click)="dialog.close()">Cerrar</button></div>
      <h2 #heading [id]="helpId + '-title'" tabindex="-1">{{ title }}</h2>
      <div class="dialog-content"><ng-content /></div>
    </dialog>
  `,
})
export class InfoDialogComponent {
  @Input({required: true}) helpId = '';
  @Input({required: true}) title = '';
  @Input() label = 'Cómo funciona';
  @ViewChild('dialog', {static: true}) dialog!: ElementRef<HTMLDialogElement>;
  @ViewChild('heading', {static: true}) heading!: ElementRef<HTMLElement>;
  @ViewChild('trigger', {static: true}) trigger!: ElementRef<HTMLButtonElement>;

  open() {
    this.dialog.nativeElement.showModal();
    this.heading.nativeElement.focus();
  }

  restoreFocus() {
    if (this.trigger.nativeElement.isConnected) this.trigger.nativeElement.focus();
  }

  containFocus(event: KeyboardEvent) {
    containDialogFocus(this.dialog.nativeElement, this.heading.nativeElement, event);
  }
}

export function containDialogFocus(dialog: HTMLDialogElement, heading: HTMLElement, event: KeyboardEvent) {
    if (event.key !== 'Tab') return;
    const controls = Array.from(dialog.querySelectorAll<HTMLElement>(
      'button:not(:disabled), a[href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex="0"]'
    )).filter(element => element.getClientRects().length > 0);
    const first = controls[0];
    const last = controls[controls.length - 1];
    const active = document.activeElement;
    if (!first) { event.preventDefault(); heading.focus(); return; }
    if (!controls.includes(active as HTMLElement) || (!event.shiftKey && active === last) || (event.shiftKey && active === first)) {
      event.preventDefault();
      (event.shiftKey ? last : first).focus();
    }
}
