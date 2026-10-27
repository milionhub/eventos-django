# ADR-0006 — Demo local con Docker; despliegue público opcional

**Estado:** Aceptado · **Fecha:** 2026-10-27

## Contexto
Presupuesto 0 €. Los planes gratuitos de hosting cambian a menudo (bases de datos que caducan, servidores que se duermen, discos efímeros).

## Decisión
- El entregable de portfolio es: **repositorio público + README con GIF/vídeo + `docker compose --profile demo up` con datos sembrados + CI en verde**.
- El despliegue público es opcional y se valorará en la Fase 7 si es viable gratis.
- Sin subida de ficheros: las imágenes de eventos se guardan como URL.

## Consecuencias
- ✅ No dependemos de terceros ni hay sorpresas de última hora.
- ⚠️ El revisor no tiene una URL en vivo; lo compensan el vídeo y el arranque en un solo comando.
