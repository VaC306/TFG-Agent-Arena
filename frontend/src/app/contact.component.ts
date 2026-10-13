import { Component } from '@angular/core';
@Component({selector:'arena-contact',standalone:true,template:`      <section class="contact-view view-enter" aria-labelledby="contact-title">
        <header class="contact-intro"><p class="eyebrow">Agent Arena / El proyecto</p><h1 id="contact-title" tabindex="-1">Contacto.</h1><p class="subheading">Un trabajo de fin de grado para la<br><strong>Universidad Complutense de Madrid.</strong></p><p class="hint">Desarrollado por Rishi Pursnani Mirpuri y Alejando Ramos Yañez.</p></header>
        <div class="contact-authors">
          <article aria-labelledby="contact-rishi"><p class="eyebrow">Autor</p><h2 id="contact-rishi">Rishi Pursnani Mirpuri</h2><address><a href="mailto:ripursna@ucm.es" aria-label="Enviar correo a Rishi Pursnani Mirpuri: ripursna@ucm.es">ripursna&#64;ucm.es <span aria-hidden="true">↗</span></a></address></article>
          <article aria-labelledby="contact-alejando"><p class="eyebrow">Autor</p><h2 id="contact-alejando">Alejando Ramos Yañez</h2><address><a href="mailto:alramo03@ucm.es" aria-label="Enviar correo a Alejando Ramos Yañez: alramo03@ucm.es">alramo03&#64;ucm.es <span aria-hidden="true">↗</span></a></address></article>
        </div>
      </section>`})
export class ContactComponent {}
