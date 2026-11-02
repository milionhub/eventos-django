# The Django API for `docker compose --profile demo`. Development does not use this image.
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_NO_CACHE=1 \
    PATH="/app/.venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=config.settings.prod

RUN pip install --no-cache-dir uv

WORKDIR /app

# Dependencies first: this layer is only rebuilt when the lock file changes.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .

# Never run as root. The two folders exist beforehand so that the named volumes mounted on
# them are created with this user as the owner.
RUN useradd --create-home --uid 1000 app \
    && mkdir -p media staticfiles \
    && chown -R app:app media staticfiles
USER app

EXPOSE 8000

# As a command and not a .sh file: Git on Windows may check scripts out with CRLF line endings,
# which break them inside a Linux container.
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py collectstatic --noinput && exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 2 --access-logfile -"]
