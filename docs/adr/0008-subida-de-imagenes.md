# ADR-0008 — Imagen del evento: subida de archivo validada y re-codificada

**Estado:** Aceptado · **Fecha:** 2026-10-28 · **Sustituye a:** la nota «sin subida de ficheros en el MVP» de `data-model.md`

## Contexto
La imagen del evento era una URL pegada a mano. En la práctica nadie tiene una URL pública de su cartel, la experiencia resultaba pobre y una app de eventos profesional deja subir la foto. Subir archivos, en cambio, es una superficie de ataque clásica: ficheros que no son imágenes, imágenes que esconden otro contenido, tamaños enormes y metadatos personales (EXIF con la ubicación GPS de una foto hecha con el móvil).

## Decisión
- `Event.image` es un `ImageField` guardado en el almacenamiento local (`MEDIA_ROOT`), sin servicios externos (coste 0 €). La API sigue exponiendo `image_url` (ruta `/media/…`), así que los clientes no cambian.
- Endpoint propio `PUT` / `DELETE organizations/{org}/events/{id}/image/` en `multipart/form-data`. El resto de la API sigue siendo solo JSON (`DEFAULT_PARSER_CLASSES`).
- Validación en el servicio (`set_event_image`):
  - Tamaño máximo **5 MB**.
  - **Pillow** abre y verifica el contenido: solo JPEG, PNG o WebP reales (no se confía en la extensión ni en el `Content-Type`).
  - Límite de píxeles para evitar «bombas de descompresión».
- La imagen se **re-codifica a WebP** (máx. 1600 px de ancho): desaparecen EXIF, perfiles y cualquier contenido incrustado, y pesa menos. Nombre de archivo aleatorio (UUID): nunca se usa el nombre que envía el cliente.
- Al sustituir o quitar la imagen se borra el archivo anterior.
- Angular recorta a 16:9 en el navegador (con encuadre elegido por el organizador) antes de subir; el backend no depende de ello y valida igualmente.

## Consecuencias
- ✅ Experiencia de app real: arrastrar, previsualizar y encuadrar.
- ✅ Las fotos del móvil no filtran la ubicación de quien las hizo.
- ✅ Dependencia nueva: **Pillow** (estándar de facto, también la exige `ImageField`).
- ⚠️ Hay que servir `/media/`: Django en desarrollo; nginx en el modo demo (Fase 7). En producción real iría a un almacenamiento de objetos.
- ⚠️ Los archivos no viajan con la base de datos: las copias de seguridad deben incluir `MEDIA_ROOT`.

## Alternativas descartadas
- **Seguir con URL:** experiencia pobre y dependiente de imágenes externas que pueden desaparecer.
- **Portadas predefinidas sin subida:** bonito pero no permite la foto propia del evento.
- **Almacenamiento en la nube (S3, Cloudinary):** innecesario para un proyecto local y fuera de presupuesto en el peor caso.
