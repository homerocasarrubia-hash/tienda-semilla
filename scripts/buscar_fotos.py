# -*- coding: utf-8 -*-
"""Busca fotos de producto por código de barras y las deja como sugerencias.

    python scripts/buscar_fotos.py                 todos los productos sin foto
    python scripts/buscar_fotos.py --limite 20     solo los próximos 20
    python scripts/buscar_fotos.py --producto 57   uno solo (por su N°)
    python scripts/buscar_fotos.py --rehacer       vuelve a buscar también lo ya buscado
    python scripts/buscar_fotos.py --lista         muestra qué buscaría, sin buscar

Busca primero en supermercados online (catálogo, fondo blanco) y, si no
aparece, en Open Food Facts. Las fotos encontradas no se publican: quedan
en el panel, en "Fotos", para que las revises (Usar / Ninguna sirve).

Con código de barras busca por código. Sin código, busca por el nombre, pero
solo en productos por unidad (envasados) y solo si el título que devuelve el
sitio se parece al nombre. Los que se venden por peso (sueltos) se saltean.
Con --incluir-sueltos busca también a los que se venden por peso.
Con --solo-codigos no busca por nombre.

Si se corta (Ctrl+C, se cae internet), volvé a correrlo: sigue desde donde
quedó, porque cada producto se anota apenas se termina de buscar.
"""
import argparse
import os
import sys

PROYECTO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROYECTO)

import buscador_fotos  # noqa: E402
import db  # noqa: E402
import fotos_sugeridas  # noqa: E402
from migrar import cargar_env  # noqa: E402


def main():
    parser = argparse.ArgumentParser(
        description='Busca fotos de producto por código de barras.')
    parser.add_argument('--limite', type=int, default=0,
                        help='cuántos productos buscar como máximo')
    parser.add_argument('--producto', type=int, default=None,
                        help='buscar solo el producto con este N°')
    parser.add_argument('--rehacer', action='store_true',
                        help='incluir también los que ya se buscaron')
    parser.add_argument('--incluir-sueltos', action='store_true',
                        help='buscar por nombre también los que se venden por peso')
    parser.add_argument('--solo-codigos', action='store_true',
                        help='no buscar por nombre a los que no tienen código')
    parser.add_argument('--lista', action='store_true',
                        help='solo mostrar qué se buscaría')
    args = parser.parse_args()

    cargar_env()

    try:
        ok, error = db.hay_conexion()
    except db.FaltaConfiguracion as e:
        print(e)
        return 1
    if not ok:
        print('No pude conectarme a la base de datos (%s).' % error)
        return 1

    pendientes = fotos_sugeridas.para_buscar(solo_id=args.producto,
                                             rehacer=args.rehacer,
                                             por_nombre=not args.solo_codigos,
                                             incluir_sueltos=args.incluir_sueltos)
    if args.limite > 0:
        pendientes = pendientes[:args.limite]

    if not pendientes:
        print('No hay nada para buscar: todos los productos sin foto que se '
              'pueden buscar ya se buscaron.\n(Los sueltos, que se venden por '
              'peso, se saltean.)')
        return 0

    print('Productos para buscar: %d' % len(pendientes))
    if args.lista:
        for p in pendientes:
            print('  %4d  %-13s  %s' % (p['id'], p['codigo'] or '(nombre)', p['nombre']))
        return 0

    sesion = buscador_fotos.nueva_sesion()
    limitador = buscador_fotos.Limitador(buscador_fotos.INTERVALO_OFF)
    limitador_texto = buscador_fotos.Limitador(buscador_fotos.INTERVALO_OFF_TEXTO)
    totales = {'con_fotos': 0, 'sin_resultados': 0, 'error': 0}
    fotos_nuevas = 0

    try:
        for numero, p in enumerate(pendientes, 1):
            if p['codigo']:
                resultado = buscador_fotos.buscar(p['codigo'], sesion=sesion,
                                                  limitador_off=limitador)
            else:
                resultado = buscador_fotos.buscar_por_nombre(
                    p['nombre'], sesion=sesion, limitador_off=limitador_texto)
            nuevas = fotos_sugeridas.registrar_busqueda(
                p['id'], p['codigo'], resultado)

            totales[resultado.estado] += 1
            fotos_nuevas += nuevas
            detalle = {
                'con_fotos': '%d foto(s) [%s]' % (
                    len(resultado.fotos),
                    resultado.fotos[0]['etiqueta'] if resultado.fotos else ''),
                'sin_resultados': 'sin resultados',
                'error': 'falló la conexión (se reintenta la próxima vez)',
            }[resultado.estado]
            print('[%d/%d] %s - %s: %s' % (numero, len(pendientes),
                                            p['codigo'] or 'por nombre',
                                            p['nombre'], detalle))
            sys.stdout.flush()
    except KeyboardInterrupt:
        print('\nCortado. Lo hecho hasta acá quedó guardado: volvé a correrlo '
              'para seguir.')

    print()
    print('Con fotos: %d · sin resultados: %d · con error: %d · fotos nuevas '
          'para revisar: %d' % (totales['con_fotos'], totales['sin_resultados'],
                                totales['error'], fotos_nuevas))
    print('Revisalas en el panel: /admin/fotos')
    return 0


if __name__ == '__main__':
    sys.exit(main())
