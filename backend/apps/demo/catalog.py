"""What the demo contains. Data only: `services.py` turns it into rows. Texts are in Spanish
because they are what the app shows, like any content typed by a real organizer."""

from dataclasses import dataclass
from datetime import timedelta
from enum import StrEnum

DEMO_DOMAIN = "@demo.test"
DEMO_PASSWORD = "Demo-Eventos-2026"


class Kind(StrEnum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    CANCELLED = "CANCELLED"


class Lucia(StrEnum):
    """What the showcase attendee does with an event, so "Mis entradas" has every state."""

    NOTHING = ""
    BOOKS = "books"
    ATTENDS = "attends"
    CANCELS = "cancels"


@dataclass(frozen=True)
class Org:
    key: str
    name: str
    slug: str  # what `unique_slug` gives for `name`; used to recognise the demo's rows
    description: str
    owner: str
    # (email local part, role)
    members: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class Category:
    name: str
    capacity: int
    fill: float = 0.0  # share of the quota booked
    description: str = ""


@dataclass(frozen=True)
class DemoEvent:
    org: str
    title: str
    location: str
    description: str
    categories: tuple[Category, ...] = ()
    image: str = ""
    day: int = 0  # days from today, at `hour` local time...
    hour: int = 21
    from_now: timedelta | None = None  # ...or this far from this very moment
    hours: int = 3
    kind: Kind = Kind.PUBLISHED
    show: float = 0.0  # share of the confirmed reservations that get scanned
    lucia: Lucia = Lucia.NOTHING


# (email local part, first name, last name, is platform admin)
STAFF_ACCOUNTS = (
    ("admin", "Ana", "Plataforma", True),
    ("marta", "Marta", "Solís", False),
    ("teo", "Teo", "Ibarra", False),
    ("ines", "Inés", "Robles", False),
    ("diego", "Diego", "Valle", False),
    ("sara", "Sara", "Quintana", False),
    ("hugo", "Hugo", "Prieto", False),
    ("nora", "Nora", "Cabrera", False),
    ("lucia", "Lucía", "Ferrer", False),
)

ORGANIZATIONS = (
    Org(
        key="nebula",
        name="Sala Nébula",
        slug="sala-nebula",
        description="Sala de conciertos con programación de jazz, rock y electrónica.",
        owner="marta",
        members=(("diego", "MANAGER"), ("hugo", "STAFF")),
    ),
    Org(
        key="teatro",
        name="Teatro de la Ribera",
        slug="teatro-de-la-ribera",
        description="Teatro de barrio: improvisación, cine, talleres y arte contemporáneo.",
        owner="teo",
        members=(("sara", "MANAGER"), ("nora", "STAFF"), ("diego", "STAFF")),
    ),
    Org(
        key="mercado",
        name="Mercado Vivo",
        slug="mercado-vivo",
        description="Colectivo de productores: catas, talleres y mercados de temporada.",
        owner="ines",
        members=(("marta", "MANAGER"),),
    ),
)

NEBULA = "Calle del Olmo 14, Madrid"
TEATRO = "Paseo del Muelle 3, Madrid"
MERCADO = "Calle de la Cebada 40, Madrid"

EVENTS = (
    # --- Today: the door is open, so the scanner has something to do -------------------------
    DemoEvent(
        org="nebula",
        title="Saxofones en Directo",
        location=NEBULA,
        description="Cuarteto de saxos y sección rítmica: dos pases de jazz con clásicos y "
        "composiciones propias. La sala abre una hora antes con servicio de barra.",
        image="jazz-sax",
        from_now=timedelta(minutes=-45),
        categories=(
            Category("General", 120, 0.85, "Acceso de pie a la sala"),
            Category("Mesa VIP", 20, 1.0, "Mesa reservada junto al escenario"),
        ),
        show=0.7,
        lucia=Lucia.BOOKS,
    ),
    DemoEvent(
        org="teatro",
        title="Improvisación sin Red",
        location=TEATRO,
        description="Una compañía, ningún guion: el público propone y los actores crean una "
        "obra distinta cada noche.",
        image="theatre-curtain",
        from_now=timedelta(hours=2),
        hours=2,
        categories=(
            Category("Patio de butacas", 80, 0.7),
            Category("Primera fila", 16, 1.0, "Puedes acabar sobre el escenario"),
        ),
        show=0.12,
        lucia=Lucia.BOOKS,
    ),
    # --- Coming up ---------------------------------------------------------------------------
    DemoEvent(
        org="nebula",
        title="Cráter: Gira de Presentación",
        location=NEBULA,
        description="El trío de rock madrileño estrena su segundo disco en directo, con "
        "invitados sorpresa y una puesta en escena pensada para la sala.",
        image="rock-stage",
        day=3,
        categories=(
            Category("Pista", 150, 0.94),
            Category("Grada", 60, 0.9, "Vista elevada y asientos"),
        ),
        lucia=Lucia.BOOKS,
    ),
    DemoEvent(
        org="mercado",
        title="Mercado de Productores de Otoño",
        location=MERCADO,
        description="Más de treinta productores de la región: fruta, queso, pan de masa madre "
        "y conservas. Entrada con degustación incluida.",
        image="market",
        day=4,
        hour=11,
        hours=8,
        categories=(Category("Entrada", 300, 0.32),),
        lucia=Lucia.BOOKS,
    ),
    DemoEvent(
        org="teatro",
        title="Cine en Butaca: Clásicos Restaurados",
        location=TEATRO,
        description="Sesión doble de clásicos en copia restaurada, con presentación a cargo de "
        "la filmoteca del barrio.",
        image="cinema-seats",
        day=6,
        hour=19,
        hours=4,
        categories=(Category("Butaca", 90, 0.42),),
        lucia=Lucia.CANCELS,
    ),
    DemoEvent(
        org="mercado",
        title="Cata a Ciegas: Tintos de Autor",
        location=MERCADO,
        description="Seis vinos sin etiqueta y una sumiller que no da pistas hasta el final. "
        "Plazas muy limitadas.",
        image="wine",
        day=8,
        hour=20,
        hours=2,
        categories=(Category("Plaza", 24, 1.0),),
    ),
    DemoEvent(
        org="nebula",
        title="Nébula Club: Sesión de Electrónica",
        location=NEBULA,
        description="Cinco horas de house y techno con tres DJ residentes y visuales en directo.",
        image="dj-party",
        day=9,
        hour=23,
        hours=5,
        categories=(
            Category("Anticipada", 40, 1.0, "Hasta agotar existencias"),
            Category("General", 160, 0.55),
        ),
    ),
    DemoEvent(
        org="mercado",
        title="Taller de Café de Especialidad",
        location=MERCADO,
        description="Del grano a la taza: molienda, extracción y arte latte con una campeona "
        "nacional de barismo.",
        image="dinner",
        day=11,
        hour=10,
        hours=3,
        categories=(Category("Plaza", 16, 0.81),),
    ),
    DemoEvent(
        org="teatro",
        title="Taller de Cortometraje en un Día",
        location=TEATRO,
        description="Escribe, rueda y monta un corto en una jornada. Trae tu móvil: nosotros "
        "ponemos el resto del equipo.",
        image="meeting-room",
        day=12,
        hour=9,
        hours=9,
        categories=(Category("Plaza", 20, 0.95),),
    ),
    DemoEvent(
        org="nebula",
        title="Vinilos y Vermú",
        location=NEBULA,
        description="Mañana de escucha colectiva: cada asistente trae un disco y lo presenta. "
        "El vermú corre de nuestra cuenta.",
        image="vinyl",
        day=16,
        hour=12,
        categories=(Category("Entrada", 40, 1.0),),
    ),
    DemoEvent(
        org="teatro",
        title="Luz y Sombra: Instalaciones de Arte",
        location=TEATRO,
        description="Recorrido nocturno por doce instalaciones lumínicas de artistas emergentes.",
        image="light-art",
        day=18,
        hour=19,
        hours=4,
        categories=(
            Category("General", 150, 0.36),
            Category("Visita guiada", 25, 0.6, "Con la comisaria de la exposición"),
        ),
    ),
    DemoEvent(
        org="mercado",
        title="Cena Maridada a Cuatro Manos",
        location=MERCADO,
        description="Dos cocineras, siete pases y un vino para cada uno. Menú de temporada con "
        "producto del mercado.",
        image="dinner",
        day=20,
        categories=(Category("Menú", 36, 0.61),),
    ),
    DemoEvent(
        org="nebula",
        title="Brunch con Trompeta",
        location=NEBULA,
        description="Jazz tranquilo de mañana y brunch casero. Ambiente familiar: los menores "
        "entran gratis acompañados.",
        image="trumpet",
        day=23,
        hour=11,
        categories=(Category("General", 60, 0.2),),
    ),
    DemoEvent(
        org="teatro",
        title="Círculo de Percusión Africana",
        location=TEATRO,
        description="Taller abierto y concierto final con djembés. No hace falta experiencia.",
        day=27,
        hour=18,
        categories=(Category("General", 70, 0.11),),
    ),
    DemoEvent(
        org="nebula",
        title="Taller de DJ para Principiantes",
        location=NEBULA,
        description="Aprende a mezclar en cabinas profesionales, en grupos reducidos.",
        image="dj-controller",
        day=30,
        hour=17,
        categories=(Category("Plaza", 12, 0.75),),
    ),
    DemoEvent(
        org="mercado",
        title="Yoga al Amanecer",
        location=MERCADO,
        description="Sesión para todos los niveles a la salida del sol, con desayuno al terminar.",
        image="yoga",
        day=33,
        hour=7,
        hours=2,
        categories=(Category("Esterilla", 50, 0.16),),
    ),
    DemoEvent(
        org="mercado",
        title="Encuadernación Artesanal",
        location=MERCADO,
        description="Cose y encuaderna tu propio cuaderno con técnicas tradicionales. Recién "
        "publicado: todavía no tiene reservas.",
        day=40,
        hour=10,
        categories=(Category("Plaza", 14),),
    ),
    DemoEvent(
        org="mercado",
        title="Feria de Invierno",
        location=MERCADO,
        description="Atracciones, puestos de comida y música en directo durante todo el día.",
        image="fair",
        day=45,
        hour=12,
        hours=10,
        categories=(Category("Entrada", 400, 0.05),),
    ),
    DemoEvent(
        org="nebula",
        title="Gran Fiesta de Fin de Año",
        location=NEBULA,
        description="Despedimos el año con dos bandas en directo, DJ hasta el amanecer y "
        "campanadas en el escenario.",
        day=55,
        hour=23,
        hours=6,
        categories=(
            Category("Early Bird", 50, 1.0, "Primeras plazas"),
            Category("General", 200, 0.3),
            Category("VIP", 30, 0.4, "Zona reservada con barra propia"),
        ),
    ),
    # --- Finished: stats and attendance ------------------------------------------------------
    DemoEvent(
        org="teatro",
        title="Encuentro de Programadores Culturales",
        location=TEATRO,
        description="Jornada profesional sobre programación en salas pequeñas.",
        image="meeting-room",
        day=-7,
        hour=10,
        hours=6,
        categories=(Category("Asistente", 40, 0.95),),
        show=0.95,
    ),
    DemoEvent(
        org="nebula",
        title="Festival Confeti",
        location=NEBULA,
        description="Doce bandas emergentes en dos escenarios y un final con lluvia de confeti.",
        image="confetti",
        day=-12,
        hour=18,
        hours=7,
        categories=(
            Category("General", 180, 0.9),
            Category("Abono VIP", 40, 1.0, "Acceso a backstage"),
        ),
        show=0.88,
        lucia=Lucia.ATTENDS,
    ),
    DemoEvent(
        org="mercado",
        title="Picnic Sonoro al Aire Libre",
        location="Parque de la Dehesa, Madrid",
        description="Música acústica y comida de productores sobre la hierba.",
        image="open-air",
        day=-21,
        hour=12,
        hours=6,
        categories=(Category("Entrada", 250, 0.8),),
        show=0.72,
    ),
    DemoEvent(
        org="nebula",
        title="Noche de Bandas Emergentes",
        location=NEBULA,
        description="Cuatro grupos, veinte minutos cada uno, y el público elige al ganador.",
        day=-30,
        categories=(Category("General", 120, 0.78),),
        show=0.8,
        lucia=Lucia.BOOKS,  # booked and did not turn up
    ),
    DemoEvent(
        org="teatro",
        title="Charla: Programar un Teatro Pequeño",
        location=TEATRO,
        description="Una tarde con quienes programan salas de menos de doscientas butacas.",
        day=-45,
        hour=19,
        hours=2,
        categories=(Category("Asistente", 60, 0.5),),
        show=0.66,
    ),
    # --- Cancelled and drafts ----------------------------------------------------------------
    DemoEvent(
        org="nebula",
        title="Concierto Acústico en la Azotea",
        location="Azotea del Mirador, Madrid",
        description="Un concierto íntimo al atardecer con vistas a toda la ciudad.",
        day=14,
        hour=20,
        categories=(Category("General", 50, 0.7),),
        kind=Kind.CANCELLED,
        lucia=Lucia.BOOKS,
    ),
    DemoEvent(
        org="teatro",
        title="Gala de Primavera",
        location=TEATRO,
        description="Borrador: falta cerrar el reparto.",
        day=90,
        categories=(Category("Patio de butacas", 120), Category("Palco", 24)),
        kind=Kind.DRAFT,
    ),
    DemoEvent(
        org="teatro",
        title="Ciclo de Documental",
        location=TEATRO,
        description="Borrador sin categorías: todavía no se puede publicar.",
        day=70,
        hour=19,
        kind=Kind.DRAFT,
    ),
    DemoEvent(
        org="mercado",
        title="Cata de Vermús de Reus",
        location=MERCADO,
        description="Borrador: pendiente de confirmar a la bodega.",
        day=60,
        hour=13,
        categories=(Category("Plaza", 30),),
        kind=Kind.DRAFT,
    ),
)

# One string each: as list literals, the formatter would spread them over 100 lines.
FIRST_NAMES = (  # noqa: SIM905
    "Adrián Alba Álvaro Amaya Andrea Ángel Aitana Bruno Carla Carlos Carmen Claudia Daniel Elena "
    "Emma Enzo Eva Fátima Gabriel Gonzalo Irene Iván Javier Jimena Jorge Julia Laura León Leire "
    "Manuel María Mario Martina Mateo Miguel Naia Nerea Nicolás Noa Óscar Pablo Paula Pedro Rocío "
    "Rubén Sergio Sofía Tomás Valeria Vera"
).split()
LAST_NAMES = (  # noqa: SIM905
    "Aguilar Alonso Arias Benítez Blanco Bravo Caballero Calvo Campos Cano Castro Cortés Crespo "
    "Delgado Díez Domínguez Durán Esteban Fuentes Gallego Garrido Gil Giménez Herrera Hidalgo "
    "Iglesias León Lozano Marín Medina Méndez Molina Montero Mora Moreno Navarro Nieto Ortega "
    "Pascual Peña Prieto Ramos Reyes Rivas Román Rubio Sáez Santos Serrano Vega"
).split()
