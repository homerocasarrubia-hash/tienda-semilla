"""Conexión a la base de datos (Postgres / Neon).

La URL sale siempre de la variable de entorno DATABASE_URL. No se guarda
ni se imprime en ningún lado.
"""
import os

from sqlalchemy import (Column, Integer, MetaData, Numeric, String, Table,
                        Text, create_engine)

TABLA_POR_DEFECTO = 'productos'

_motor = None
_metadata = MetaData()
_tablas = {}


class FaltaConfiguracion(RuntimeError):
    """DATABASE_URL no está definida."""


AYUDA = """
No encuentro la dirección de la base de datos.

El sitio la lee de la variable DATABASE_URL. Agregá esta línea al archivo
.env que está en la carpeta del proyecto:

    DATABASE_URL=postgresql://usuario:clave@host/base?sslmode=require

Ese dato lo da el panel de Neon, en "Connection string". El archivo .env
no se sube al repositorio, así que la clave no queda expuesta.
""".strip()


def url_de_conexion():
    url = os.environ.get('DATABASE_URL', '').strip()

    if not url:
        raise FaltaConfiguracion(AYUDA)

    # Algunos proveedores entregan "postgres://", que SQLAlchemy 2 ya no
    # acepta. El resto de la URL —incluido sslmode=require— se respeta tal
    # cual: psycopg2 lo interpreta solo, no hace falta configurarlo aparte.
    if url.startswith('postgres://'):
        url = 'postgresql://' + url[len('postgres://'):]

    return url


def motor():
    """El engine, creado una sola vez y recién cuando se lo necesita."""
    global _motor

    if _motor is None:
        _motor = create_engine(
            url_de_conexion(),
            # Neon suspende la base cuando no hay tráfico y corta las
            # conexiones ociosas: sin esto, la primera consulta después de
            # un rato falla.
            pool_pre_ping=True,
            pool_recycle=280,
            pool_size=5,
            max_overflow=5,
            # Que un error de SQL no vuelque los valores en el log
            hide_parameters=True,
        )

    return _motor


def tabla(nombre=TABLA_POR_DEFECTO):
    """Definición de la tabla de productos.

    `orden` no estaba en el JSON: guarda la posición que cada producto tenía
    en el archivo. Sin esa columna habría que ordenar por id, y 155 de los
    417 productos aparecerían en otro lugar de la grilla.
    """
    if nombre not in _tablas:
        _tablas[nombre] = Table(
            nombre, _metadata,
            Column('id', Integer, primary_key=True, autoincrement=False),
            Column('orden', Integer, nullable=False, default=0),
            Column('nombre', Text, nullable=False),
            Column('descripcion', Text, nullable=False, server_default=''),
            Column('categoria', Text, nullable=False),
            Column('subcategoria', Text, nullable=True),
            Column('imagen', Text, nullable=True),
            Column('stock', String(20), nullable=False, server_default='disponible'),
            Column('precio', Numeric(12, 2), nullable=True),
            Column('precio_100g', Numeric(12, 2), nullable=True),
            Column('precio_kg', Numeric(12, 2), nullable=True),
            extend_existing=True,
        )

    return _tablas[nombre]


def crear_tabla(nombre=TABLA_POR_DEFECTO):
    """CREATE TABLE IF NOT EXISTS, más los índices que usan los filtros."""
    from sqlalchemy import Index, text

    t = tabla(nombre)
    t.create(motor(), checkfirst=True)

    with motor().begin() as cx:
        cx.execute(text('CREATE INDEX IF NOT EXISTS idx_%s_categoria '
                        'ON %s (categoria)' % (nombre, nombre)))
        cx.execute(text('CREATE INDEX IF NOT EXISTS idx_%s_subcategoria '
                        'ON %s (subcategoria)' % (nombre, nombre)))
        cx.execute(text('CREATE INDEX IF NOT EXISTS idx_%s_orden '
                        'ON %s (orden)' % (nombre, nombre)))

    return t


def hay_conexion():
    """Prueba la conexión sin filtrar la URL en el mensaje de error."""
    from sqlalchemy import text

    try:
        with motor().connect() as cx:
            cx.execute(text('SELECT 1'))
        return True, ''
    except FaltaConfiguracion:
        raise
    except Exception as e:
        # El texto de la excepción puede traer la URL: se recorta al tipo
        return False, type(e).__name__
