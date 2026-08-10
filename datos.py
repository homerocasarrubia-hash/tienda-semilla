"""Acceso al catálogo, guardado en Postgres.

La forma de los productos que ve el resto de la aplicación es la misma que
tenía el JSON: un diccionario por producto, **sin las claves que están en
nulo**. Un producto a granel no tiene la clave "precio", y uno por unidad
no tiene "precio_100g" ni "precio_kg", que es de lo que dependen las
plantillas para distinguirlos.
"""
import os

from sqlalchemy import delete, func, insert, or_, select, update
from sqlalchemy.sql import case

import db

CARPETA = os.path.dirname(os.path.abspath(__file__))
CARPETA_IMAGENES = os.path.join(CARPETA, 'static', 'img')
RUTA_JSON = os.path.join(CARPETA, 'productos.json')

# Orden en que se arma cada diccionario, para que el JSON exportado quede
# igual al de siempre.
_ORDEN_CLAVES = ('id', 'nombre', 'descripcion', 'precio_100g', 'precio_kg',
                 'precio', 'categoria', 'subcategoria', 'imagen', 'stock')

ESTADOS_STOCK = (
    ('disponible', 'Disponible'),
    ('ultimas', 'Últimas unidades'),
    ('sin_stock', 'Sin stock'),
)
_CLAVES_STOCK = {clave for clave, _ in ESTADOS_STOCK}

_cache_imagenes = None
_cache_imagenes_mtime = None

# La tabla se puede cambiar para correr pruebas contra otra
_tabla = db.tabla()


def usar_tabla(nombre):
    """Apunta el módulo a otra tabla (lo usan las pruebas)."""
    global _tabla
    _tabla = db.tabla(nombre)
    return _tabla


def tabla():
    return _tabla


# --- conversión entre filas y diccionarios -------------------------------

def _numero(valor):
    """Decimal -> int cuando es redondo, para que 2000.00 vuelva a ser 2000."""
    if valor is None:
        return None
    flotante = float(valor)
    return int(flotante) if flotante == int(flotante) else flotante


def _a_dict(fila):
    mapa = fila._mapping
    producto = {}

    for clave in _ORDEN_CLAVES:
        if clave not in mapa:
            continue
        valor = mapa[clave]
        if valor is None:
            # La clave directamente no existe, igual que en el JSON
            continue
        if clave in ('precio', 'precio_100g', 'precio_kg'):
            valor = _numero(valor)
        producto[clave] = valor

    return producto


def _valores(producto):
    """Diccionario -> columnas. Lo que no está pasa a NULL."""
    return {
        'nombre': producto.get('nombre', ''),
        'descripcion': producto.get('descripcion', '') or '',
        'categoria': producto.get('categoria', ''),
        'subcategoria': producto.get('subcategoria') or None,
        'imagen': producto.get('imagen') or None,
        'stock': estado_stock(producto),
        'precio': producto.get('precio'),
        'precio_100g': producto.get('precio_100g'),
        'precio_kg': producto.get('precio_kg'),
    }


def _filas(consulta):
    with db.motor().connect() as cx:
        return [_a_dict(f) for f in cx.execute(consulta)]


# --- estado de stock (sin tocar la base) ---------------------------------

def estado_stock(producto):
    """Tolera que el campo falte o venga con un valor desconocido."""
    valor = (producto.get('stock') or '').strip()
    return valor if valor in _CLAVES_STOCK else 'disponible'


def sin_stock(producto):
    return estado_stock(producto) == 'sin_stock'


def nombres_sin_stock():
    consulta = (select(_tabla.c.nombre)
                .where(_tabla.c.stock == 'sin_stock')
                .order_by(_tabla.c.orden))
    with db.motor().connect() as cx:
        return [f[0] for f in cx.execute(consulta)]


# --- lecturas -------------------------------------------------------------

def cargar():
    """Todo el catálogo en el orden del catálogo (el que usa el panel)."""
    return _filas(select(_tabla).order_by(_tabla.c.orden, _tabla.c.id))


def obtener(id_producto):
    filas = _filas(select(_tabla).where(_tabla.c.id == id_producto))
    return filas[0] if filas else None


def siguiente_id():
    with db.motor().connect() as cx:
        maximo = cx.execute(select(func.max(_tabla.c.id))).scalar()
    return (maximo or 0) + 1


def _siguiente_orden(cx):
    maximo = cx.execute(select(func.max(_tabla.c.orden))).scalar()
    return (maximo or 0) + 1


def categorias():
    with db.motor().connect() as cx:
        crudas = cx.execute(select(_tabla.c.categoria).distinct()).scalars()
        # El orden se resuelve en Python: así no depende del "collation" de
        # la base y queda igual que cuando el catálogo era un archivo.
        return sorted({c for c in crudas if c})


def subcategorias():
    with db.motor().connect() as cx:
        crudas = cx.execute(select(_tabla.c.subcategoria).distinct()).scalars()
        return sorted({s for s in crudas if s})


def existe_nombre(nombre, categoria, excepto_id=None):
    consulta = select(func.count()).select_from(_tabla).where(
        func.lower(func.btrim(_tabla.c.nombre)) == nombre.strip().lower(),
        func.lower(func.btrim(_tabla.c.categoria)) == categoria.strip().lower(),
    )
    if excepto_id is not None:
        consulta = consulta.where(_tabla.c.id != excepto_id)

    with db.motor().connect() as cx:
        return cx.execute(consulta).scalar() > 0


# --- filtros de la tienda -------------------------------------------------

def _orden_publico():
    """Los agotados al final; dentro de cada grupo, el orden del catálogo."""
    return (case((_tabla.c.stock == 'sin_stock', 1), else_=0), _tabla.c.orden)


def _empieza_alguna_palabra(palabra):
    """Equivale a: alguna palabra del nombre empieza con `palabra`."""
    escapada = palabra.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
    nombre = func.lower(_tabla.c.nombre)
    return or_(nombre.like(escapada + '%', escape='\\'),
               nombre.like('% ' + escapada + '%', escape='\\'))


def catalogo_ordenado():
    return _filas(select(_tabla).order_by(*_orden_publico()))


def filtrar_por_categoria(cat):
    return _filas(select(_tabla)
                  .where(_tabla.c.categoria == cat)
                  .order_by(*_orden_publico()))


def filtrar_sin_tacc():
    """La categoría "Sin TACC" junta además lo que lo aclara en el nombre."""
    return _filas(select(_tabla)
                  .where(or_(_tabla.c.categoria == 'Sin TACC',
                             func.lower(_tabla.c.nombre).contains('sin tacc',
                                                                  autoescape=True)))
                  .order_by(*_orden_publico()))


def filtrar_por_subcategoria(subcat):
    return _filas(select(_tabla)
                  .where(_tabla.c.subcategoria == subcat)
                  .order_by(*_orden_publico()))


def filtrar_por_texto(busqueda):
    """Cada palabra tiene que aparecer en el nombre, la descripción, la
    categoría o la subcategoría."""
    condiciones = []
    for palabra in busqueda.lower().split():
        condiciones.append(or_(
            _empieza_alguna_palabra(palabra),
            func.lower(_tabla.c.descripcion).contains(palabra, autoescape=True),
            func.lower(_tabla.c.categoria).contains(palabra, autoescape=True),
            func.lower(func.coalesce(_tabla.c.subcategoria, ''))
                .contains(palabra, autoescape=True),
        ))

    consulta = select(_tabla)
    for condicion in condiciones:
        consulta = consulta.where(condicion)

    return _filas(consulta.order_by(*_orden_publico()))


def autocompletar(busqueda, limite=8):
    """Sugerencias del buscador: solo por nombre, con el mismo puntaje."""
    consulta = select(_tabla.c.nombre, _tabla.c.categoria, _tabla.c.stock)

    for palabra in busqueda.split():
        consulta = consulta.where(_empieza_alguna_palabra(palabra))

    escapada = busqueda.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
    nombre = func.lower(_tabla.c.nombre)
    puntaje = case(
        (nombre.like(escapada + '%', escape='\\'), 0),
        (nombre.like('% ' + escapada + '%', escape='\\'), 1),
        (nombre.contains(busqueda, autoescape=True), 2),
        else_=3,
    )

    # Empates: el orden del catálogo, igual que el sort estable de antes
    consulta = consulta.order_by(puntaje, _tabla.c.orden).limit(limite)

    with db.motor().connect() as cx:
        return [{'nombre': f.nombre, 'categoria': f.categoria,
                 'stock': f.stock if f.stock in _CLAVES_STOCK else 'disponible'}
                for f in cx.execute(consulta)]


# --- altas, cambios y bajas ----------------------------------------------

def crear(producto):
    valores = _valores(producto)

    with db.motor().begin() as cx:
        maximo = cx.execute(select(func.max(_tabla.c.id))).scalar()
        valores['id'] = (maximo or 0) + 1
        valores['orden'] = _siguiente_orden(cx)
        cx.execute(insert(_tabla).values(**valores))

    return obtener(valores['id'])


def actualizar(id_producto, producto):
    valores = _valores(producto)

    with db.motor().begin() as cx:
        resultado = cx.execute(update(_tabla)
                               .where(_tabla.c.id == id_producto)
                               .values(**valores))
        if resultado.rowcount == 0:
            return None

    return obtener(id_producto)


def eliminar(id_producto):
    producto = obtener(id_producto)
    if producto is None:
        return None

    with db.motor().begin() as cx:
        cx.execute(delete(_tabla).where(_tabla.c.id == id_producto))

    return producto


def actualizar_precios(cambios):
    """Aplica varios cambios de precio de una sola vez.

    Solo toca los campos de precio que el producto ya tiene: a un producto
    a granel no se le carga un "precio" suelto.
    """
    if not cambios:
        return 0

    modificados = 0

    with db.motor().begin() as cx:
        filas = cx.execute(select(_tabla).where(_tabla.c.id.in_(list(cambios)))).all()

        for fila in filas:
            actual = _a_dict(fila)
            nuevos = cambios.get(actual['id']) or {}
            pendientes = {}

            for clave, valor in nuevos.items():
                if clave in actual and actual[clave] != valor:
                    pendientes[clave] = valor

            if pendientes:
                cx.execute(update(_tabla)
                           .where(_tabla.c.id == actual['id'])
                           .values(**pendientes))
                modificados += 1

    return modificados


def reemplazar_todo(lista):
    """Vacía la tabla y carga la lista entera. Lo usa la migración."""
    with db.motor().begin() as cx:
        cx.execute(delete(_tabla))
        for posicion, producto in enumerate(lista):
            valores = _valores(producto)
            valores['id'] = producto['id']
            valores['orden'] = posicion
            cx.execute(insert(_tabla).values(**valores))
    return len(lista)


def contar():
    with db.motor().connect() as cx:
        return cx.execute(select(func.count()).select_from(_tabla)).scalar()


# --- imágenes (siguen viviendo en el disco) ------------------------------

def imagenes_disponibles():
    global _cache_imagenes, _cache_imagenes_mtime

    try:
        mtime = os.path.getmtime(CARPETA_IMAGENES)
    except OSError:
        _cache_imagenes = set()
        _cache_imagenes_mtime = None
        return _cache_imagenes

    if _cache_imagenes is None or mtime != _cache_imagenes_mtime:
        try:
            _cache_imagenes = {n.lower() for n in os.listdir(CARPETA_IMAGENES)}
        except OSError:
            _cache_imagenes = set()
        _cache_imagenes_mtime = mtime

    return _cache_imagenes


def imagen_existe(nombre):
    return bool(nombre) and nombre.lower() in imagenes_disponibles()
