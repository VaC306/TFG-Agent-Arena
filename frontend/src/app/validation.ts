/** Count Unicode characters as the API does, without trimming meaningful input. */
export function textError(value: unknown, label: string, max: number, required = true): string {
  if (typeof value !== 'string') return `${label}: escribe texto válido.`;
  if (/\u0000|[\uD800-\uDBFF](?![\uDC00-\uDFFF])|(?<![\uD800-\uDBFF])[\uDC00-\uDFFF]/u.test(value)) return `${label}: contiene caracteres no válidos.`;
  if (required && !value.trim()) return `${label}: este campo es obligatorio.`;
  if ([...value].length > max) return `${label}: máximo ${max} caracteres.`;
  return '';
}

export function passwordError(value: string, register: boolean): string {
  return textError(value, 'Contraseña', 128, register) ||
    ([...value].length < (register ? 10 : 1) ? (register ? 'La contraseña necesita al menos 10 caracteres.' : 'Escribe tu contraseña.') : '');
}

export const modelIdentity = (model: string) => model.includes(':') ? model : model + ':latest';

export function filenameError(name: string): string {
  return textError(name, 'Nombre del archivo', 180) || (/[\\/\x00-\x1f\x7f]/.test(name) ? 'El nombre del archivo contiene caracteres no admitidos.' : '');
}

/** Mirrors strict CSV quoting: quoted cells may contain commas and line breaks. */
export function csvError(text: string): string {
  let quoted = false, start = true, closed = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (quoted) {
      if (c === '"') { if (text[i + 1] === '"') i++; else { quoted = false; closed = true; } }
    } else if (c === ',' || c === '\n' || c === '\r') { start = true; closed = false; }
    else if (closed) return 'CSV inválido: después de cerrar las comillas debe terminar el campo.';
    else if (start && c === '"') { quoted = true; start = false; }
    else start = false;
  }
  return quoted ? 'CSV inválido: hay comillas sin cerrar.' : '';
}
