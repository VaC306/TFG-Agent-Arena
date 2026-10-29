"""Bounded text-only PDF ingestion, run in a time-limited child process."""
import io
import json
import sys


def extract(raw):
    from pypdf import PdfReader, filters
    filters.ZLIB_MAX_OUTPUT_LENGTH = 2*1024*1024
    reader = PdfReader(io.BytesIO(raw),strict=True)
    if reader.is_encrypted:
        raise ValueError('No se admiten PDF cifrados')
    if not 1<=len(reader.pages)<=20:
        raise ValueError('El PDF debe tener entre 1 y 20 páginas')
    parts = []
    has_text = False
    for index,page in enumerate(reader.pages):
        contents = page.get_contents()
        if contents and len(contents.get_data())>1024*1024:
            raise ValueError('Una página PDF supera el límite de contenido descomprimido')
        text = page.extract_text() or ''
        has_text = has_text or bool(text.strip())
        parts.append(f'Página {index+1}\n{text}')
        if sum(map(len,parts))>20000:
            raise ValueError('El texto PDF supera 20.000 caracteres')
    if not has_text:
        raise ValueError('El PDF no tiene texto extraíble. Los escaneos requieren OCR, que no está incluido.')
    return '\n\n'.join(parts)


if __name__=='__main__':
    try:
        raw = sys.stdin.buffer.read(1024*1024+1)
        if not raw.startswith(b'%PDF-') or len(raw)>1024*1024:
            raise ValueError('PDF inválido o superior a 1 MiB')
        result = {'text':extract(raw)}
    except Exception as exc:
        result = {'error':str(exc)[:500]}
    sys.stdout.buffer.write(json.dumps(result,ensure_ascii=False).encode('utf-8'))
