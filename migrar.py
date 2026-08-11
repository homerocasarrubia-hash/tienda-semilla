# -*- coding: utf-8 -*-
"""Migración del catálogo de productos.json a Postgres, y vuelta.

    python migrar.py              importa el JSON a la base (idempotente)
    python migrar.py --reiniciar  vacía la tabla antes de importar
    python migrar.py --exportar   vuelca la base a productos.json (backup)

Por defecto usa "upsert" por id: correrlo dos veces no duplica nada y no
borra lo que se haya cargado desde el panel. La URL de la base sale de
DATABASE_URL; nunca se imprime ni se guarda.
"""
import argparse
import io
import json
import os
import sys

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as insert_pg

import datos
import db


def cargar_env():
    """Lee el .env, igual que app.py. Lo que ya esté en el entorno gana."""
    ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    try:
        with open(ruta, encoding='utf-8-sig') as f:
            lineas = f.readlines()
    except FileNotFoundError:
        return

    for linea in lineas:
        linea = linea.strip()
        if not linea or linea.startswith('#') or '=' not in linea:
            continue
        clave, _, valor = linea.partition('=')
        clave = clave.strip()
        valor = valor.strip().strip('"').strip("'")
        if clave and clave not in os.environ:
            os.environ[clave] = valor


def leer_json():
    with io.open(datos.RUTA_JSON, encoding='utf-8') as f:
        return json.load(f)


def escribir_json(lista):
    temporal = datos.RUTA_JSON + '.tmp'
    with io.open(temporal, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(lista, f, ensure_ascii=False, indent=2)
        f.write('\n')
    os.replace(temporal, datos.RUTA_JSON)


def importar(reiniciar=False):
    productos = leer_json()
    print('productos en productos.json: %d' % len(productos))

    tabla = db.crear_tabla()
    db.crear_tabla_descuentos()
    print('tablas listas (se crearon si no existían)')

    if reiniciar:
        with db.motor().begin() as cx:
            borradas = cx.execute(tabla.delete()).rowcount
        print('tabla vaciada: %d filas borradas' % borradas)

    insertados = 0
    actualizados = 0

    with db.motor().begin() as cx:
        for posicion, producto in enumerate(productos):
            valores = datos._valores(producto)
            valores['id'] = producto['id']
            valores['orden'] = posicion

            # Upsert: si el id ya está, se pisa; si no, se inserta.
            sentencia = insert_pg(tabla).values(**valores)
            sentencia = sentencia.on_conflict_do_update(
                index_elements=[tabla.c.id],
                set_={k: sentencia.excluded[k] for k in valores if k != 'id'},
            )
            resultado = cx.execute(sentencia)
            # rowcount no distingue insert de update en un upsert, así que se
            # cuenta aparte más abajo con el total.
            insertados += resultado.rowcount

    # --- control final: la base tiene que tener lo mismo que el archivo ---
    with db.motor().connect() as cx:
        en_base = cx.execute(select(func.count()).select_from(tabla)).scalar()
        ids_base = {f[0] for f in cx.execute(select(tabla.c.id))}

    ids_json = {p['id'] for p in productos}

    print()
    print('filas en la base : %d' % en_base)
    print('productos en JSON: %d' % len(productos))

    problemas = []
    if en_base != len(productos):
        problemas.append('la cantidad no coincide (base %d, archivo %d)'
                         % (en_base, len(productos)))
    faltan = ids_json - ids_base
    if faltan:
        problemas.append('faltan en la base los ids: %s' % sorted(faltan)[:20])
    sobran = ids_base - ids_json
    if sobran:
        problemas.append('hay en la base ids que no están en el archivo: %s '
                         '(si los cargó el panel, está bien: usá --exportar '
                         'para actualizar el backup)' % sorted(sobran)[:20])

    if problemas:
        print()
        print('LA MIGRACION NO CIERRA:')
        for p in problemas:
            print('  - %s' % p)
        return 1

    print('los %d productos están en la base, con los mismos ids' % en_base)
    return 0


def exportar():
    db.crear_tabla()
    productos = datos.cargar()

    if not productos:
        print('La base está vacía: no se escribe nada, para no pisar el backup.')
        return 1

    escribir_json(productos)
    print('exportados %d productos a %s' % (len(productos), datos.RUTA_JSON))

    # Control: releer y comparar
    releidos = leer_json()
    if len(releidos) != len(productos):
        print('EL ARCHIVO NO QUEDO BIEN: %d en la base, %d en el archivo'
              % (len(productos), len(releidos)))
        return 1
    print('archivo verificado: %d productos' % len(releidos))
    return 0


def main():
    parser = argparse.ArgumentParser(
        description='Migra el catálogo entre productos.json y Postgres.')
    parser.add_argument('--reiniciar', action='store_true',
                        help='vacía la tabla antes de importar')
    parser.add_argument('--exportar', action='store_true',
                        help='vuelca la base a productos.json (backup)')
    args = parser.parse_args()

    cargar_env()

    try:
        ok, error = db.hay_conexion()
    except db.FaltaConfiguracion as e:
        print(e)
        return 1

    if not ok:
        print('No pude conectarme a la base de datos (%s).\n'
              'Revisá que DATABASE_URL sea correcta y que la base de Neon\n'
              'esté activa.' % error)
        return 1

    if args.exportar:
        return exportar()

    return importar(reiniciar=args.reiniciar)


if __name__ == '__main__':
    sys.exit(main())
