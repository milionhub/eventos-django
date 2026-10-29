// Django for the E2E tests: its own database (created if missing, migrated and emptied) on
// port 8001, so the development server and data on 8000 are never touched.
import { execFileSync, spawn } from 'node:child_process';
import { existsSync, readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const backend = fileURLToPath(new URL('../../backend/', import.meta.url));
const dotenv = fileURLToPath(new URL('../../.env', import.meta.url));

// CI passes E2E_DATABASE_URL; locally, the development URL with another database name.
function databaseUrl() {
  if (process.env.E2E_DATABASE_URL) return process.env.E2E_DATABASE_URL;
  const line = existsSync(dotenv)
    ? readFileSync(dotenv, 'utf8')
        .split(/\r?\n/)
        .find((l) => l.startsWith('DATABASE_URL='))
    : undefined;
  const url = new URL(
    line?.slice('DATABASE_URL='.length) ?? 'postgres://eventos:eventos@127.0.0.1:5432/eventos',
  );
  url.pathname = '/eventos_e2e';
  return url.toString();
}

const env = {
  ...process.env,
  DATABASE_URL: databaseUrl(),
  DJANGO_DEBUG: 'True',
  DJANGO_ALLOWED_HOSTS: 'localhost,127.0.0.1',
  // Every test signs in from the same IP: the real limits would turn them into 429s.
  THROTTLE_LOGIN_RATE: '10000/min',
  THROTTLE_REGISTER_RATE: '10000/min',
  THROTTLE_REFRESH_RATE: '10000/min',
  THROTTLE_RESERVATIONS_RATE: '10000/min',
  THROTTLE_CHECKIN_RATE: '10000/min',
};

const CREATE_DATABASE = `
import os, psycopg
from urllib.parse import urlsplit
url = urlsplit(os.environ["DATABASE_URL"])
name = url.path.lstrip("/")
with psycopg.connect(url._replace(path="/postgres").geturl(), autocommit=True) as conn:
    if not conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", [name]).fetchone():
        conn.execute(f'CREATE DATABASE "{name}"')
`;

const run = (args) => execFileSync('uv', ['run', ...args], { cwd: backend, env, stdio: 'inherit' });
run(['python', '-c', CREATE_DATABASE]);
run(['python', 'manage.py', 'migrate', '--no-input', '-v', '0']);
run(['python', 'manage.py', 'flush', '--no-input']);

const server = spawn(
  'uv',
  ['run', 'python', 'manage.py', 'runserver', '127.0.0.1:8001', '--noreload'],
  {
    cwd: backend,
    env,
    stdio: 'inherit',
  },
);
for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => server.kill(signal));
server.on('exit', (code) => process.exit(code ?? 0));
