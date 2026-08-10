"""Acceso al catálogo guardado en productos.json.

El resto de la aplicación no lee ni escribe el archivo directamente: todo
pasa por acá, para que la caché y el guardado atómico valgan siempre.
"""
import io
import json
import os
import shutil
import threading

CARPETA = os.path.dirname(os.path.abspath(__file__))
RUTA = os.path.join(CARPETA, 'productos.json')
RUTA_BACKUP = RUTA + '.bak'
CARPETA_IMAGENES = os.path.join(CARPETA, 'static', 'img')

# Orden de las claves con el que se escribe cada producto, para que el JSON
# se mantenga legible y estable entre guardados.
_ORDEN_CLAVES = ('id', 'nombre', 'descripcion', 'precio_100g', 'precio_kg',
                 'precio', 'categoria', 'subcategoria', 'imagen', 'stock')

# Estados de stock. El primero es el valor por defecto.
ESTADOS_STOCK = (
    ('disponible', 'Disponible'),
    ('ultimas', 'Últimas unidades'),
    ('sin_stock', 'Sin stock'),
)
_CLAVES_STOCK = {clave for clave, _ in ESTADOS_STOCK}

_cache = None
_cache_mtime = None
_cache_imagenes = None
_cache_imagenes_mtime = None
_candado = threading.Lock()


def cargar():
    """Devuelve la lista de productos, recargando si el archivo cambió.

    La lista devuelta es la interna: quien la modifique tiene que hacerlo
    sobre una copia (ver obtener()) y volver a llamar a guardar().
    """
    global _cache, _cache_mtime

    try:
        mtime = os.path.getmtime(RUTA)
    except FileNotFoundError:
        return []

    if _cache is None or mtime != _cache_mtime:
        with io.open(RUTA, encoding='utf-8') as f:
            _cache = json.load(f)
        _cache_mtime = mtime

    return _cache


def guardar(lista):
    """Escribe el catálogo entero.

    Primero deja una copia de seguridad del archivo anterior y después
    escribe en un temporal que reemplaza al original de una sola vez: si el
    proceso se corta a la mitad, productos.json nunca queda incompleto.
    """
    global _cache, _cache_mtime

    ordenada = [_ordenar_claves(p) for p in lista]

    with _candado:
        if os.path.exists(RUTA):
            shutil.copy2(RUTA, RUTA_BACKUP)

        temporal = RUTA + '.tmp'
        with io.open(temporal, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(ordenada, f, ensure_ascii=False, indent=2)
            f.write('\n')

        os.replace(temporal, RUTA)

        _cache = ordenada
        _cache_mtime = os.path.getmtime(RUTA)

    return ordenada


def _ordenar_claves(producto):
    ordenado = {k: producto[k] for k in _ORDEN_CLAVES if k in producto}
    # Cualquier clave que no esté en la lista de arriba se conserva igual
    for k, v in producto.items():
        if k not in ordenado:
            ordenado[k] = v
    return ordenado


# --- consultas -----------------------------------------------------------

def obtener(id_producto):
    """Copia del producto con ese id, o None. Es copia para que editarla no
    toque la caché hasta que se guarde."""
    for p in cargar():
        if p.get('id') == id_producto:
            return dict(p)
    return None


def siguiente_id():
    ids = [p.get('id', 0) for p in cargar()]
    return (max(ids) + 1) if ids else 1


def categorias():
    return sorted({p.get('categoria', '') for p in cargar() if p.get('categoria')})


def subcategorias():
    return sorted({p.get('subcategoria', '') for p in cargar() if p.get('subcategoria')})


def estado_stock(producto):
    """El estado del producto, tolerando que el campo falte o venga raro.

    Los productos viejos pueden no tener el campo, y nunca hay que romper
    por eso: cualquier valor desconocido cuenta como disponible.
    """
    valor = (producto.get('stock') or '').strip()
    return valor if valor in _CLAVES_STOCK else 'disponible'


def sin_stock(producto):
    return estado_stock(producto) == 'sin_stock'


def nombres_sin_stock():
    """Nombres de los productos agotados, para que el carrito los detecte."""
    return [p['nombre'] for p in cargar() if sin_stock(p)]


def imagenes_disponibles():
    """Archivos que hay en static/img/.

    Se relee solo cuando cambia la fecha de la carpeta, así preguntar por
    cientos de productos en una misma página cuesta un stat y no cientos de
    listados. Como no cachea para siempre, las fotos nuevas aparecen sin
    reiniciar el servidor.
    """
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
    """Si el archivo de foto del producto está realmente en static/img/."""
    return bool(nombre) and nombre.lower() in imagenes_disponibles()


def existe_nombre(nombre, categoria, excepto_id=None):
    """Para avisar de posibles duplicados al cargar un producto nuevo."""
    nombre = nombre.strip().lower()
    categoria = categoria.strip().lower()
    for p in cargar():
        if p.get('id') == excepto_id:
            continue
        if p.get('nombre', '').strip().lower() == nombre and \
           p.get('categoria', '').strip().lower() == categoria:
            return True
    return False


# --- altas, cambios y bajas ---------------------------------------------

def crear(producto):
    lista = [dict(p) for p in cargar()]
    producto = dict(producto)
    producto['id'] = siguiente_id()
    lista.append(producto)
    guardar(lista)
    return producto


def actualizar(id_producto, producto):
    lista = [dict(p) for p in cargar()]
    for i, p in enumerate(lista):
        if p.get('id') == id_producto:
            producto = dict(producto)
            producto['id'] = id_producto
            lista[i] = producto
            guardar(lista)
            return producto
    return None


def eliminar(id_producto):
    lista = [dict(p) for p in cargar()]
    for i, p in enumerate(lista):
        if p.get('id') == id_producto:
            borrado = lista.pop(i)
            guardar(lista)
            return borrado
    return None


def actualizar_precios(cambios):
    """Aplica varios cambios de precio de una sola vez.

    cambios: {id: {'precio_100g': 1500, ...}}. Devuelve cuántos productos
    quedaron efectivamente modificados.
    """
    lista = [dict(p) for p in cargar()]
    modificados = 0

    for p in lista:
        nuevos = cambios.get(p.get('id'))
        if not nuevos:
            continue
        cambio_este = False
        for clave, valor in nuevos.items():
            # Solo se tocan los campos de precio que el producto ya tiene
            if clave in p and p[clave] != valor:
                p[clave] = valor
                cambio_este = True
        if cambio_este:
            modificados += 1

    if modificados:
        guardar(lista)

    return modificados
