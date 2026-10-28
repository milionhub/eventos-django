# Architecture Decision Records

Cada decisión técnica relevante se documenta con: **Contexto → Decisión → Consecuencias → Alternativas descartadas**.
Si una decisión cambia, no se edita el ADR: se crea uno nuevo que lo sustituye y el antiguo se marca como *Sustituido*.

| # | Decisión | Estado |
|---|---|---|
| [0001](0001-monolito-modular.md) | Monolito modular Django + SPA Angular | Aceptado |
| [0002](0002-usuario-propio-email.md) | Modelo de usuario propio con login por email | Aceptado |
| [0003](0003-autenticacion-jwt.md) | JWT con refresh en cookie httpOnly | Aceptado |
| [0004](0004-concurrencia-reservas-checkin.md) | Concurrencia: UPDATE condicional + restricciones de BD | Aceptado |
| [0005](0005-reservas-con-cuenta.md) | Reservas solo con cuenta, 1 entrada por reserva | Aceptado |
| [0006](0006-sin-despliegue-obligatorio.md) | Demo local con Docker; despliegue público opcional | Aceptado |
| [0007](0007-cliente-api-generado.md) | Cliente Angular generado a partir de OpenAPI | Aceptado |
| [0008](0008-subida-de-imagenes.md) | Imagen del evento: subida validada y re-codificada | Aceptado |
