"""Códigos de descuento.

Módulo aparte del catálogo: son datos independientes y no comparten nada
con la tabla de productos.

Importante sobre el alcance: el descuento se calcula y se muestra del lado
del navegador, y el pedido se cierra por WhatsApp. Esto sirve para que el
cliente vea el precio con descuento, no para hacerlo cumplir. Ver la nota
en el README de la conversación / respuesta.
"""
from sqlalchemy import delete, func, insert, select, update

import db

MINIMO = 1
MAXIMO = 100


def _tabla():
    return db.tabla_descuentos()


def _a_dict(fila):
    return {
        'id': fila.id,
        'codigo': fila.codigo,
        'porcentaje': fila.porcentaje,
        'activo': fila.activo,
        'creado_en': fila.creado_en,
    }


def listar():
    """Todos los códigos, del más nuevo al más viejo."""
    consulta = select(_tabla()).order_by(_tabla().c.creado_en.desc(),
                                         _tabla().c.id.desc())
    with db.motor().connect() as cx:
        return [_a_dict(f) for f in cx.execute(consulta)]


def obtener(id_descuento):
    consulta = select(_tabla()).where(_tabla().c.id == id_descuento)
    with db.motor().connect() as cx:
        fila = cx.execute(consulta).first()
    return _a_dict(fila) if fila else None


def buscar_por_codigo(codigo):
    """Busca sin distinguir mayúsculas. Devuelve el código aunque esté
    desactivado: quien pregunta decide qué hacer."""
    codigo = (codigo or '').strip()
    if not codigo:
        return None

    consulta = select(_tabla()).where(
        func.lower(func.btrim(_tabla().c.codigo)) == codigo.lower())
    with db.motor().connect() as cx:
        fila = cx.execute(consulta).first()
    return _a_dict(fila) if fila else None


def validar(codigo):
    """Lo que consulta la tienda: el código puntual, y solo si está activo.

    Devuelve el diccionario del descuento o None. Nunca devuelve listados.
    """
    encontrado = buscar_por_codigo(codigo)
    if encontrado is None or not encontrado['activo']:
        return None
    return encontrado


def existe(codigo, excepto_id=None):
    encontrado = buscar_por_codigo(codigo)
    if encontrado is None:
        return False
    return excepto_id is None or encontrado['id'] != excepto_id


def revisar(codigo, porcentaje_texto):
    """Valida lo que se cargó en el formulario.

    Devuelve (codigo_limpio, porcentaje, errores) con mensajes en castellano
    llano, sin nombres de campos internos.
    """
    errores = []

    codigo = (codigo or '').strip()
    if not codigo:
        errores.append('Escribí el código, por ejemplo BIENVENIDA10.')
    elif len(codigo) > 40:
        errores.append('El código es demasiado largo: usá hasta 40 letras.')
    elif existe(codigo):
        errores.append('Ya existe un código igual a «%s». Los códigos no '
                       'distinguen mayúsculas de minúsculas.' % codigo)

    porcentaje = None
    texto = (porcentaje_texto or '').strip().replace('%', '')

    if not texto:
        errores.append('Poné el porcentaje de descuento, por ejemplo 10.')
    else:
        try:
            porcentaje = int(float(texto.replace(',', '.')))
        except ValueError:
            errores.append('El porcentaje tiene que ser un número. '
                           'Escribí solo el número, sin el signo %.')
        else:
            if not (MINIMO <= porcentaje <= MAXIMO):
                errores.append('El porcentaje tiene que estar entre %d y %d.'
                               % (MINIMO, MAXIMO))

    return codigo, porcentaje, errores


def crear(codigo, porcentaje):
    with db.motor().begin() as cx:
        cx.execute(insert(_tabla()).values(codigo=codigo.strip(),
                                           porcentaje=int(porcentaje),
                                           activo=True))
    return buscar_por_codigo(codigo)


def cambiar_activo(id_descuento, valor):
    with db.motor().begin() as cx:
        resultado = cx.execute(update(_tabla())
                               .where(_tabla().c.id == id_descuento)
                               .values(activo=bool(valor)))
        if resultado.rowcount == 0:
            return None
    return obtener(id_descuento)


def eliminar(id_descuento):
    encontrado = obtener(id_descuento)
    if encontrado is None:
        return None

    with db.motor().begin() as cx:
        cx.execute(delete(_tabla()).where(_tabla().c.id == id_descuento))

    return encontrado


def contar():
    with db.motor().connect() as cx:
        return cx.execute(select(func.count()).select_from(_tabla())).scalar()
