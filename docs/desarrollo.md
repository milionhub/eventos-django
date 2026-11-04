# Desarrollo

Para probar la aplicación sin instalar nada más que Docker, basta el [comando del README](../README.md#pruébalo). Esta guía es para trabajar en el código.

### Requisitos
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (para PostgreSQL)
- [uv](https://docs.astral.sh/uv/) (instala Python 3.13 automáticamente)
- [Node.js 24](https://nodejs.org/)

### Primera vez
```bash
cp .env.example .env               # valores de desarrollo; cambia DJANGO_SECRET_KEY
docker compose up -d db            # PostgreSQL 17

cd backend
uv sync
uv run python manage.py migrate
uv run python manage.py createsuperuser   # opcional, para entrar en /admin/
uv run pre-commit install                 # ruff y prettier antes de cada commit

cd ../frontend
npm install
```

### Arrancar
En dos terminales:
```bash
cd backend && uv run python manage.py runserver   # API en http://127.0.0.1:8000/api/docs/
cd frontend && npm start                          # web en http://localhost:4200
```
Angular redirige `/api` a Django mediante un proxy, así que basta con abrir `http://localhost:4200`.

### Datos de demostración
```bash
cd backend && uv run python manage.py seed_demo            # tarda menos de un minuto
cd backend && uv run python manage.py seed_demo --reset    # la vuelve a crear con fechas de hoy
```
Crea 3 organizaciones, 28 eventos y unas 1600 reservas con sus escaneos, con eventos agotados, en curso, terminados, cancelados y en borrador. Las fechas son relativas al momento de ejecutarlo. Todo pasa por los servicios reales, así que los contadores cuadran. `--reset` solo borra lo que creó la demo. Las cuentas están en el [README](../README.md#pruébalo). Con `DEBUG=False` el comando exige `--force`, porque las contraseñas son públicas. Las fotos son CC0: [créditos](../backend/apps/demo/CREDITS.md).

### Tests y calidad
| | Backend (`backend/`) | Frontend (`frontend/`) |
|---|---|---|
| Tests | `uv run pytest` | `npm test` |
| Cobertura | `uv run pytest --cov` (mínimo 98 %; la CI falla por debajo) | — |
| De extremo a extremo | — | `npm run e2e` (Playwright: los 5 recorridos en escritorio y en móvil, accesibilidad con axe y uso con teclado) |
| Lint | `uv run ruff check .` | `npm run lint` |
| Formato | `uv run ruff format .` | `npm run format` |
| Vulnerabilidades | `uv export --frozen --no-emit-project > req.txt && uvx pip-audit -r req.txt --disable-pip` | `npm audit --audit-level=high` |

Los tests del backend usan PostgreSQL (nunca SQLite), así que el contenedor `db` debe estar arrancado.

La CI ejecuta las dos auditorías en cada cambio y, además, todos los lunes, para enterarse de las vulnerabilidades nuevas aunque no se toque el código.

### Tests de extremo a extremo
`npm run e2e` (en `frontend/`) recorre los 5 recorridos de [`requirements.md`](requirements.md) §2 con clics reales en Chromium, a 1280 px y en un Pixel 7 emulado:
1. el organizador crea y publica un evento;
2. el asistente reserva una entrada;
3. el asistente cancela su reserva;
4. el personal de acceso valida entradas;
5. el organizador consulta los resultados y exporta el CSV.

Los tests arrancan su propio Django en el puerto 8001, con una base de datos `eventos_e2e` que se vacía en cada ejecución, y el build de producción en el 4300. Así no tocan el entorno de desarrollo, que puede seguir abierto mientras corren. Lo único que necesitan es el contenedor `db` arrancado. La primera vez hay que descargar el navegador: `npx playwright install chromium`.

En la CI se ejecutan en un workflow propio (`e2e`). Si algo falla, el informe con la traza de cada test se guarda como artefacto (`npx playwright show-trace`).

### Cliente de la API
El cliente Angular se genera a partir del esquema OpenAPI de Django ([ADR-0007](adr/0007-cliente-api-generado.md)). Tras cambiar la API:
```bash
cd frontend && npm run api:generate   # actualiza backend/schema.yml y src/app/core/api/
```
La CI falla si alguno de los dos queda desactualizado.

### Probar el escáner en un móvil
La cámara del móvil solo funciona con HTTPS, así que se expone el servidor de desarrollo con un túnel gratuito de [cloudflared](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/do-more-with-tunnels/trycloudflare/). Paso a paso en la [guía para el móvil](guia-movil.md).

> ⚠️ Mientras el túnel está abierto, la aplicación (con `DEBUG` activado) es accesible desde internet. Ciérralo al terminar.
