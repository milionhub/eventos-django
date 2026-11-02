# ADR-0009 — Margen de 30 s para el refresh recién rotado

**Estado:** Aceptado · **Fecha:** 2026-11-02 · **Matiza a:** [ADR-0003](0003-autenticacion-jwt.md)

## Contexto
Con rotación y blacklist (ADR-0003), cada carga de página cambia el token de refresh. Si el usuario navega justo mientras esa petición está en curso, el servidor ya ha invalidado el token anterior, pero el navegador cancela la petición y nunca guarda el nuevo. En la siguiente carga envía el token invalidado y la sesión se pierde. Se reprodujo en un navegador real al probar la demo: recargar y navegar sin esperar. En móvil, donde la petición tarda más, es más fácil que ocurra.

## Decisión
- Un token sustituido por la rotación sigue valiendo **30 s** (`REFRESH_REUSE_GRACE_SECONDS`). Si se reutiliza, se emite uno nuevo.
- El sustituido se marca en la caché, sin migración. Si la caché pierde la marca, se rechaza, que es el comportamiento anterior y el más seguro.
- La marca solo se pone a tokens que aún no estaban invalidados, y reutilizarlos no alarga el plazo.
- **El logout no da margen.** Bloquea el margen de ese usuario durante esos 30 s, para que ningún token anterior reabra la sesión.
- Sigue rechazándose un token caducado, manipulado o de un usuario desactivado.
- La marca se pone antes de rotar, así que las peticiones simultáneas con la misma cookie no se expulsan entre sí.

## Alternativas
- **Quitar la rotación:** elimina el problema, pero un token robado valdría los 7 días completos sin que nada lo invalide.
- **Quitar el blacklist tras rotar:** el mismo efecto, porque los tokens anteriores seguirían válidos hasta caducar.
- **Renovar menos a menudo o solo cuando caduca el acceso:** el token de acceso vive en memoria y se pierde en cada carga, así que no se evita.
- **Guardar la marca en una tabla:** sobrevive a reinicios, pero añade una migración y escrituras para un dato que vive 30 s.

## Consecuencias
- Un token robado justo después de rotar se puede usar durante esos 30 s. Es un riesgo acotado, porque la cookie es `httpOnly`.
- Si alguien vuelve pasados los 30 s tras perder la respuesta, tendrá que entrar otra vez. Es poco frecuente y no expone datos.
- En un despliegue con varios procesos, la caché debe ser compartida. `prod.py` ya usa `DatabaseCache` para los límites de peticiones.
- Con varias sesiones del mismo usuario, cerrar una deja a las demás sin margen durante 30 s. Solo afecta a quien además pierda una renovación en ese momento.
