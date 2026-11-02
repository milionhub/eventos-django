from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.demo.catalog import DEMO_DOMAIN, DEMO_PASSWORD
from apps.demo.services import DemoDataExists, remove_demo, seed_demo

ACCOUNTS = (
    ("admin", "administradora de plataforma (/admin/)"),
    ("marta", "propietaria de Sala Nébula, gestora de Mercado Vivo"),
    ("teo", "propietario de Teatro de la Ribera"),
    ("ines", "propietaria de Mercado Vivo"),
    ("diego", "gestor de Sala Nébula, personal de acceso de Teatro de la Ribera"),
    ("sara", "gestora de Teatro de la Ribera"),
    ("hugo", "personal de acceso de Sala Nébula"),
    ("nora", "personal de acceso de Teatro de la Ribera"),
    ("lucia", "asistente con entradas en todos los estados"),
)


class Command(BaseCommand):
    help = "Crea datos de demostración (organizaciones, usuarios por rol, eventos con imagen)."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--reset", action="store_true", help="Borra antes la demo anterior (solo la demo)."
        )
        parser.add_argument(
            "--attendees", type=int, default=320, help="Asistentes ficticios (320 por defecto)."
        )
        parser.add_argument(
            "--if-empty",
            action="store_true",
            help="Si ya hay datos de la demo, no hace nada en vez de dar error.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Permite ejecutarlo con DEBUG=False. Sus contraseñas son públicas: "
            "nunca en un servidor con datos reales.",
        )

    def handle(
        self, *args, reset: bool, attendees: int, if_empty: bool, force: bool, **options
    ) -> None:
        if not settings.DEBUG and not force:
            raise CommandError("Con DEBUG=False hace falta --force: las contraseñas son públicas.")
        if reset:
            remove_demo()
        try:
            summary = seed_demo(attendees=attendees)
        except DemoDataExists as exc:
            if if_empty:
                self.stdout.write("Ya hay datos de la demo: no se cambia nada.")
                return
            raise CommandError(
                "Ya hay datos de la demo, o una organización real con el mismo slug. "
                "Usa --reset para borrar la demo anterior."
            ) from exc

        self.stdout.write(
            self.style.SUCCESS(
                f"{summary.organizations} organizaciones, {summary.users} usuarios, "
                f"{summary.events} eventos, {summary.reservations} reservas, "
                f"{summary.scans} escaneos."
            )
        )
        self.stdout.write(f"Contraseña de todas las cuentas: {DEMO_PASSWORD}")
        for key, role in ACCOUNTS:
            self.stdout.write(f"  {key}{DEMO_DOMAIN}  {role}")
