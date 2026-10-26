"""Fotos sugeridas por el buscador de código de barras.

Guarda en la base (no en archivos: el disco de Render se borra en cada
reinicio) los códigos de barras, las fotos encontradas y qué productos ya
se buscaron. Quien revisa en el panel elige "Usar" o "Ninguna sirve".
"""
from sqlalchemy import and_, delete, func, insert, select, update

import buscador_fotos
import datos
import db
import imagenes

_t = {
    'codigos': db.tabla_codigos(),
    'sugerencias': db.tabla_sugerencias(),
    'busquedas': db.tabla_busquedas(),
}
_listas = False

# Estados de búsqueda que no se repiten al retomar. Los "error" sí: fue la
# red, no que el producto no tenga foto.
_TERMINADOS = ('con_fotos', 'sin_resultados')


def usar_tablas(codigos, sugerencias, busquedas):
    """Apunta el módulo a otras tablas (lo usan las pruebas)."""
    global _listas
    _t['codigos'] = db.tabla_codigos(codigos)
    _t['sugerencias'] = db.tabla_sugerencias(sugerencias)
    _t['busquedas'] = db.tabla_busquedas(busquedas)
    _listas = False


def asegurar():
    """Crea las tablas si no existen. Una vez por proceso."""
    global _listas
    if not _listas:
        db.crear_tablas_fotos(_t['codigos'].name, _t['sugerencias'].name,
                              _t['busquedas'].name)
        _listas = True


# --- códigos de barras ---------------------------------------------------

def codigo_de(id_producto):
    asegurar()
    consulta = select(_t['codigos'].c.codigo).where(
        _t['codigos'].c.producto_id == id_producto)
    with db.motor().connect() as cx:
        return cx.execute(consulta).scalar() or ''


def codigos():
    """{id_producto: codigo} de todos los que tienen."""
    asegurar()
    with db.motor().connect() as cx:
        return {f[0]: f[1] for f in cx.execute(
            select(_t['codigos'].c.producto_id, _t['codigos'].c.codigo))}


def guardar_codigo(id_producto, codigo):
    """Guarda (o borra, si viene vacío) el código ya normalizado.

    Si el código cambió, lo buscado antes ya no vale: se descartan las
    sugerencias pendientes y el producto vuelve a quedar sin buscar.
    """
    asegurar()
    c, s, b = _t['codigos'], _t['sugerencias'], _t['busquedas']

    with db.motor().begin() as cx:
        actual = cx.execute(select(c.c.codigo)
                            .where(c.c.producto_id == id_producto)).scalar()
        if (actual or '') == codigo:
            return False

        cx.execute(delete(c).where(c.c.producto_id == id_producto))
        if codigo:
            cx.execute(insert(c).values(producto_id=id_producto, codigo=codigo))

        cx.execute(delete(b).where(b.c.producto_id == id_producto))
        cx.execute(delete(s).where(and_(s.c.producto_id == id_producto,
                                        s.c.estado == 'pendiente')))
    return True


def limpiar_producto(id_producto):
    """Al eliminar un producto no deben quedar datos sueltos."""
    asegurar()
    with db.motor().begin() as cx:
        for clave in ('codigos', 'busquedas'):
            t = _t[clave]
            cx.execute(delete(t).where(t.c.producto_id == id_producto))
        s = _t['sugerencias']
        cx.execute(delete(s).where(s.c.producto_id == id_producto))


# --- qué buscar ----------------------------------------------------------

def estados_de_busqueda():
    asegurar()
    with db.motor().connect() as cx:
        return {f[0]: f[1] for f in cx.execute(
            select(_t['busquedas'].c.producto_id, _t['busquedas'].c.estado))}


def para_buscar(solo_id=None, rehacer=False, por_nombre=True):
    """Productos con código y sin foto que todavía no se buscaron.

    Sin código, se busca por el nombre solo si es un producto por unidad
    (envasado); los que se venden por peso son sueltos y se saltean.
    `por_nombre=False` limita todo a los que tienen código.
    Retomar es simplemente volver a llamar: lo ya buscado no se repite.
    `rehacer=True` incluye también lo ya buscado.
    """
    por_producto = codigos()
    hechos = estados_de_busqueda()
    salida = []

    for p in datos.cargar():
        id_producto = p['id']
        if solo_id is not None and id_producto != solo_id:
            continue
        codigo = por_producto.get(id_producto) or ''
        if datos.tiene_foto(p):
            continue
        if not codigo and not (por_nombre and 'precio_100g' not in p):
            continue
        if not rehacer and hechos.get(id_producto) in _TERMINADOS:
            continue
        salida.append({'id': id_producto, 'nombre': p['nombre'], 'codigo': codigo})

    return salida


def registrar_busqueda(id_producto, codigo, resultado):
    """Guarda el resultado de buscar un producto. Devuelve cuántas fotos nuevas."""
    asegurar()
    s, b = _t['sugerencias'], _t['busquedas']
    nuevas = 0

    with db.motor().begin() as cx:
        # Una búsqueda repetida reemplaza las pendientes; lo que ya se usó o
        # se descartó se respeta y no vuelve a sugerirse.
        cx.execute(delete(s).where(and_(s.c.producto_id == id_producto,
                                        s.c.estado == 'pendiente')))
        conocidas = {f[0] for f in cx.execute(
            select(s.c.url).where(s.c.producto_id == id_producto))}

        for posicion, foto in enumerate(resultado.fotos):
            if foto['url'] in conocidas:
                continue
            base = 0 if foto['etiqueta'] in buscador_fotos.ETIQUETAS_PRIORITARIAS else 100
            cx.execute(insert(s).values(
                producto_id=id_producto, url=foto['url'],
                etiqueta=foto['etiqueta'], fuente=foto.get('fuente', ''),
                orden=base + posicion, estado='pendiente'))
            nuevas += 1

        cx.execute(delete(b).where(b.c.producto_id == id_producto))
        cx.execute(insert(b).values(producto_id=id_producto, codigo=codigo,
                                    estado=resultado.estado))
    return nuevas


# --- revisión en el panel ------------------------------------------------

def pendientes():
    """Productos con fotos por revisar, con las de catálogo primero."""
    asegurar()
    s = _t['sugerencias']
    consulta = (select(s).where(s.c.estado == 'pendiente')
                .order_by(s.c.producto_id, s.c.orden, s.c.id))

    with db.motor().connect() as cx:
        filas = cx.execute(consulta).all()

    por_producto = {}
    for f in filas:
        por_producto.setdefault(f.producto_id, []).append({
            'id': f.id, 'url': f.url, 'etiqueta': f.etiqueta, 'fuente': f.fuente,
            'es_catalogo': f.etiqueta in buscador_fotos.ETIQUETAS_PRIORITARIAS})

    if not por_producto:
        return []

    codigos_ = codigos()
    salida = []
    for p in datos.cargar():          # en el orden del catálogo
        if p['id'] in por_producto:
            salida.append({'producto': p, 'codigo': codigos_.get(p['id'], ''),
                           'tiene_foto': datos.tiene_foto(p),
                           'fotos': por_producto[p['id']]})
    return salida


def resumen():
    asegurar()
    s = _t['sugerencias']
    por_producto = codigos()
    hechos = estados_de_busqueda()
    productos = datos.cargar()
    ids = {p['id'] for p in productos}

    sin_foto_con_codigo = [p for p in productos
                           if p['id'] in por_producto and not datos.tiene_foto(p)]

    with db.motor().connect() as cx:
        filas = cx.execute(select(s.c.producto_id, func.count())
                           .where(s.c.estado == 'pendiente')
                           .group_by(s.c.producto_id)).all()

    revisar = [f for f in filas if f[0] in ids]
    return {
        'con_codigo': sum(1 for i in por_producto if i in ids),
        'sin_foto_con_codigo': len(sin_foto_con_codigo),
        'sin_buscar': sum(1 for p in sin_foto_con_codigo
                          if hechos.get(p['id']) not in _TERMINADOS),
        'productos_por_revisar': len(revisar),
        'fotos_por_revisar': sum(f[1] for f in revisar),
    }


def descartar_producto(id_producto):
    """"Ninguna sirve": las pendientes de ese producto quedan descartadas."""
    asegurar()
    s = _t['sugerencias']
    with db.motor().begin() as cx:
        return cx.execute(update(s)
                          .where(and_(s.c.producto_id == id_producto,
                                      s.c.estado == 'pendiente'))
                          .values(estado='descartada')).rowcount


def usar(id_sugerencia, descargar=None, subir=None):
    """Asigna la foto sugerida al producto.

    El servidor descarga la imagen, la procesa y la guarda donde el
    proyecto guarda las fotos (Cloudinary). Si no puede, queda la dirección
    original, sin mostrar error: la tienda igual muestra la foto.

    Devuelve (ok, mensaje).
    """
    asegurar()
    descargar = descargar or buscador_fotos.descargar
    subir = subir or imagenes.subir
    s = _t['sugerencias']

    # Se "reclama" la sugerencia antes de bajar nada: un doble clic no
    # sube la foto dos veces.
    with db.motor().begin() as cx:
        fila = cx.execute(select(s).where(s.c.id == id_sugerencia)).first()
        if fila is None or fila.estado != 'pendiente':
            return False, 'Esa foto ya se revisó.'
        reclamada = cx.execute(update(s)
                               .where(and_(s.c.id == id_sugerencia,
                                           s.c.estado == 'pendiente'))
                               .values(estado='usada')).rowcount
        if not reclamada:
            return False, 'Esa foto ya se revisó.'

    try:
        producto = datos.obtener(fila.producto_id)
        if producto is None:
            raise LookupError

        anterior = (producto.get('imagen') or '').strip() or None
        valor = _foto_para_guardar(fila.url, descargar, subir)

        producto['imagen'] = valor
        datos.actualizar(fila.producto_id, producto)
    except Exception:
        # Que se pueda volver a intentar
        with db.motor().begin() as cx:
            cx.execute(update(s).where(s.c.id == id_sugerencia)
                       .values(estado='pendiente'))
        return False, 'No se pudo guardar. Probá de nuevo en un rato.'

    with db.motor().begin() as cx:
        cx.execute(update(s)
                   .where(and_(s.c.producto_id == fila.producto_id,
                               s.c.estado == 'pendiente'))
                   .values(estado='descartada'))

    # Recién con el producto guardado se limpia la foto reemplazada
    if anterior and anterior != valor:
        try:
            imagenes.borrar(anterior)
        except Exception:
            pass

    return True, '«%s» ya tiene su foto.' % producto['nombre']


def _foto_para_guardar(url, descargar, subir):
    crudo = descargar(url)
    if crudo:
        try:
            return subir(crudo)
        except Exception:
            # Foto rara o servicio de fotos caído: se usa la dirección
            # original, que la tienda puede mostrar igual
            pass
    return url
