import { Component, Input } from '@angular/core';
const terms = {
  model: {title:'Qué es un modelo',text:'Es el programa que genera una respuesta. Por ejemplo, un modelo local instalado en Ollama. En el simulador solo pruebas el funcionamiento de la plataforma.'},
  prompt: {title:'Qué es un prompt',text:'Son las instrucciones para el modelo. Por ejemplo: «Resume en una frase». A y B pueden recibir instrucciones iguales o diferentes.'},
  dataset: {title:'Qué es un dataset',text:'Es una lista de casos de prueba. Cada fila contiene una entrada, un identificador y, si la tienes, una respuesta esperada. Por ejemplo: saludo, «Di hola», hola.'},
  reference: {title:'Qué es una referencia',text:'Es la respuesta esperada que aportas para evaluar. Por ejemplo, «hola». No se envía al modelo. Sin referencia, no se puntúa la calidad; puedes revisar la respuesta tú mismo.'},
  run: {title:'Qué es una ejecución',text:'Es un intento de responder a un caso con una variante. Un caso, dos variantes y una repetición programan dos ejecuciones. Finalizada no significa correcta.'},
  campaign: {title:'Qué es una campaña',text:'Agrupa intentos nuevos del mismo diseño fijado: datos, referencias, prompts y parámetros. Sirve para examinar variaciones; los intentos incompatibles se explican y se excluyen del análisis compatible.'},
};
@Component({selector:'arena-term-help',standalone:true,template:`<details class="term-help"><summary>{{ entry.title }}</summary><p class="hint">{{ entry.text }}</p></details>`})
export class TermHelpComponent {
  @Input({required:true}) term: keyof typeof terms = 'model';
  get entry() { return terms[this.term]; }
}
