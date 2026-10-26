"""Conexión a la base de datos (Postgres / Neon).

La URL sale siempre de la variable de entorno DATABASE_URL. No se guarda
ni se imprime en ningún lado.
"""
import os

from sqlalchemy import (Boolean, Column, DateTime, Integer, MetaData, Numeric,
                        String, Table, Text, create_engine, func)

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

    # SQLAlchemy 2.1 cambió el driver por defecto de "postgresql://" a
    # psycopg 3, que acá no está instalado. Se fija psycopg2 de forma
    # explícita para que no dependa de qué versión instale Render.
    if url.startswith('postgresql://'):
        url = 'postgresql+psycopg2://' + url[len('postgresql://'):]

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
            Column('es_oferta', Boolean, nullable=False, server_default='false'),
            Column('es_novedad', Boolean, nullable=False, server_default='false'),
            extend_existing=True,
        )

    return _tablas[nombre]


# Columnas que se agregaron después de la primera versión de la tabla. Se
# aplican con ALTER TABLE sobre la tabla existente: nunca se recrea nada ni
# se tocan los datos que ya están cargados.
COLUMNAS_AGREGADAS = (
    ('es_oferta', 'BOOLEAN NOT NULL DEFAULT FALSE'),
    ('es_novedad', 'BOOLEAN NOT NULL DEFAULT FALSE'),
)


TABLA_DESCUENTOS = 'descuentos'


def tabla_descuentos(nombre=TABLA_DESCUENTOS):
    """Códigos de descuento. Tabla aparte: no toca nada de productos."""
    if nombre not in _tablas:
        _tablas[nombre] = Table(
            nombre, _metadata,
            Column('id', Integer, primary_key=True),
            Column('codigo', Text, nullable=False),
            Column('porcentaje', Integer, nullable=False),
            Column('activo', Boolean, nullable=False, server_default='true'),
            Column('creado_en', DateTime(timezone=True),
                   server_default=func.now(), nullable=False),
            extend_existing=True,
        )

    return _tablas[nombre]


def crear_tabla_descuentos(nombre=TABLA_DESCUENTOS):
    from sqlalchemy import text

    t = tabla_descuentos(nombre)
    t.create(motor(), checkfirst=True)

    with motor().begin() as cx:
        # La unicidad del código no distingue mayúsculas: la garantiza la
        # base, no solo la validación de Python.
        cx.execute(text('CREATE UNIQUE INDEX IF NOT EXISTS idx_%s_codigo '
                        'ON %s (lower(codigo))' % (nombre, nombre)))

    return t


# --- buscador de fotos por código de barras ------------------------------
# Tablas aparte (solo aditivo): no se toca la de productos, así el sitio
# publicado sigue funcionando igual aunque estas todavía no existan.

TABLA_CODIGOS = 'codigos_barras'
TABLA_SUGERENCIAS = 'fotos_sugeridas'
TABLA_BUSQUEDAS = 'busqueda_fotos'


def tabla_codigos(nombre=TABLA_CODIGOS):
    """Código de barras de cada producto (los sueltos no tienen)."""
    if nombre not in _tablas:
        _tablas[nombre] = Table(
            nombre, _metadata,
            Column('producto_id', Integer, primary_key=True, autoincrement=False),
            Column('codigo', Text, nullable=False),
            extend_existing=True,
        )
    return _tablas[nombre]


def tabla_sugerencias(nombre=TABLA_SUGERENCIAS):
    """Fotos encontradas, a la espera de que alguien las revise."""
    if nombre not in _tablas:
        _tablas[nombre] = Table(
            nombre, _metadata,
            Column('id', Integer, primary_key=True),
            Column('producto_id', Integer, nullable=False),
            Column('url', Text, nullable=False),
            Column('etiqueta', Text, nullable=False),
            Column('fuente', Text, nullable=False, server_default=''),
            Column('orden', Integer, nullable=False, server_default='0'),
            # pendiente | usada | descartada
            Column('estado', String(12), nullable=False, server_default='pendiente'),
            Column('creado_en', DateTime(timezone=True),
                   server_default=func.now(), nullable=False),
            extend_existing=True,
        )
    return _tablas[nombre]


def tabla_busquedas(nombre=TABLA_BUSQUEDAS):
    """Qué productos ya se buscaron: es lo que permite retomar si se corta."""
    if nombre not in _tablas:
        _tablas[nombre] = Table(
            nombre, _metadata,
            Column('producto_id', Integer, primary_key=True, autoincrement=False),
            Column('codigo', Text, nullable=False),
            # con_fotos | sin_resultados | error
            Column('estado', String(16), nullable=False),
            Column('buscado_en', DateTime(timezone=True),
                   server_default=func.now(), nullable=False),
            extend_existing=True,
        )
    return _tablas[nombre]


def crear_tablas_fotos(codigos=TABLA_CODIGOS, sugerencias=TABLA_SUGERENCIAS,
                       busquedas=TABLA_BUSQUEDAS):
    """CREATE TABLE IF NOT EXISTS de las tres tablas. Idempotente."""
    from sqlalchemy import text

    tablas = (tabla_codigos(codigos), tabla_sugerencias(sugerencias),
              tabla_busquedas(busquedas))
    for t in tablas:
        t.create(motor(), checkfirst=True)

    with motor().begin() as cx:
        # Una misma foto no se sugiere dos veces para el mismo producto
        cx.execute(text('CREATE UNIQUE INDEX IF NOT EXISTS idx_%s_unica '
                        'ON %s (producto_id, url)' % (sugerencias, sugerencias)))

    return tablas


def crear_tabla(nombre=TABLA_POR_DEFECTO):
    """CREATE TABLE IF NOT EXISTS, las columnas nuevas y los índices."""
    from sqlalchemy import text

    t = tabla(nombre)
    t.create(motor(), checkfirst=True)

    with motor().begin() as cx:
        for columna, definicion in COLUMNAS_AGREGADAS:
            cx.execute(text('ALTER TABLE %s ADD COLUMN IF NOT EXISTS %s %s'
                            % (nombre, columna, definicion)))

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
