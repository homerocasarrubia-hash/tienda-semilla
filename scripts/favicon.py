# -*- coding: utf-8 -*-
"""Genera el favicon del sitio a partir de static/logosemilla.png.

    python scripts/favicon.py

Produce en static/:
    favicon.ico            (16, 32 y 48 px en un solo archivo)
    favicon-32x32.png
    favicon-16x16.png
    apple-touch-icon.png   (180 px, para cuando alguien guarda la página
                            en la pantalla de inicio del celular)

Sobre el recorte: el logo original es una insignia hexagonal sobre un
fondo gris degradado que ocupa casi la mitad del lienzo. Escalar eso
directo dejaría la marca diminuta y rodeada de gris, así que primero se
recorta al trazo de la insignia y después se completa a cuadrado.
"""
import argparse
import os
import sys

CARPETA = os.path.dirname(os.path.abspath(__file__))
PROYECTO = os.path.dirname(CARPETA)
ESTATICOS = os.path.join(PROYECTO, 'static')
ORIGEN = os.path.join(ESTATICOS, 'logosemilla.png')

# El fondo gris ronda el 69-102 de luminosidad y el trazo de la insignia
# está por debajo de 60: con eso alcanza para separarlos.
UMBRAL_TRAZO = 60

# Aire alrededor de la marca, como proporción del lado mayor del recorte
MARGEN = 0.06

FONDO = (255, 255, 255)

# Variante "inicial": la S de Semilla en el verde de la marca, igual que el
# placeholder de las cards. Es la unica forma de que se lea algo en 16 px:
# el logotipo completo, a ese tamano, queda en una mancha gris.
VERDE = (27, 94, 74)          # --verde-700
CARPETA_FUENTES = os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
FUENTES = ("cambriab.ttf", "georgiab.ttf", "constanb.ttf", "timesbd.ttf")


class _SinOpciones(object):
    inicial = False


ARGUMENTOS = _SinOpciones()

TAMANOS_ICO = [(16, 16), (32, 32), (48, 48)]
SALIDAS_PNG = [
    ('favicon-32x32.png', 32),
    ('favicon-16x16.png', 16),
    ('apple-touch-icon.png', 180),
]


def sobre_fondo(imagen):
    """Aplana la transparencia sobre blanco."""
    if imagen.mode in ('RGBA', 'LA', 'P'):
        from PIL import Image
        imagen = imagen.convert('RGBA')
        plano = Image.new('RGB', imagen.size, FONDO)
        plano.paste(imagen, mask=imagen.split()[-1])
        return plano
    return imagen.convert('RGB')


def recortar_a_la_marca(imagen):
    """Devuelve (recorte, caja) quedándose solo con la insignia.

    Se guía por el trazo oscuro, que es lo único bien separado del fondo:
    el hexágono y las letras. Si no encuentra nada, devuelve la imagen
    entera en vez de romper.
    """
    marca = imagen.convert('L').point(lambda v: 255 if v < UMBRAL_TRAZO else 0)
    caja = marca.getbbox()

    if caja is None:
        return imagen, None

    ancho, alto = caja[2] - caja[0], caja[3] - caja[1]
    aire = int(max(ancho, alto) * MARGEN)

    caja = (max(0, caja[0] - aire),
            max(0, caja[1] - aire),
            min(imagen.width, caja[2] + aire),
            min(imagen.height, caja[3] + aire))

    return imagen.crop(caja), caja


def a_cuadrado(imagen):
    """Completa a cuadrado centrando, sin deformar la marca."""
    from PIL import Image

    lado = max(imagen.size)
    lienzo = Image.new('RGB', (lado, lado), FONDO)
    lienzo.paste(imagen, ((lado - imagen.width) // 2,
                          (lado - imagen.height) // 2))
    return lienzo


def marca_inicial(lado=944, letra="S"):
    """Dibuja la inicial en el verde de la marca, centrada."""
    from PIL import Image, ImageDraw, ImageFont

    lienzo = Image.new("RGB", (lado, lado), VERDE)
    dibujo = ImageDraw.Draw(lienzo)

    fuente = None
    for nombre in FUENTES:
        try:
            fuente = ImageFont.truetype(os.path.join(CARPETA_FUENTES, nombre),
                                        int(lado * 0.62))
            break
        except OSError:
            continue
    if fuente is None:
        fuente = ImageFont.load_default()

    caja = dibujo.textbbox((0, 0), letra, font=fuente)
    dibujo.text(((lado - (caja[2] - caja[0])) / 2 - caja[0],
                 (lado - (caja[3] - caja[1])) / 2 - caja[1]),
                letra, font=fuente, fill=FONDO)
    return lienzo


def main():
    try:
        from PIL import Image
    except ImportError:
        print('Falta Pillow. Instalalo con:\n\n    pip install -r requirements.txt')
        return 1

    if not os.path.exists(ORIGEN):
        print('No encuentro el logo en %s' % ORIGEN)
        return 1

    if ARGUMENTOS.inicial:
        print("variante: la inicial S sobre el verde de la marca")
        return escribir(marca_inicial())

    original = Image.open(ORIGEN)
    print('logo original : %s  %s' % (original.size, original.mode))

    plano = sobre_fondo(original)
    recorte, caja = recortar_a_la_marca(plano)

    if caja:
        print('recorte a la marca: %s -> %s' % (plano.size, recorte.size))
        print('   (se descartó el fondo gris de alrededor)')
    else:
        print('AVISO: no se pudo aislar la marca; se usa el logo entero.')

    cuadrado = a_cuadrado(recorte)
    print('cuadrado      : %s' % (cuadrado.size,))
    return escribir(cuadrado)


def escribir(cuadrado):
    from PIL import Image
    print()

    generados = []

    ruta_ico = os.path.join(ESTATICOS, 'favicon.ico')
    cuadrado.save(ruta_ico, format='ICO', sizes=TAMANOS_ICO)
    generados.append(ruta_ico)

    for nombre, lado in SALIDAS_PNG:
        ruta = os.path.join(ESTATICOS, nombre)
        cuadrado.resize((lado, lado), Image.LANCZOS).save(ruta, format='PNG',
                                                          optimize=True)
        generados.append(ruta)

    for ruta in generados:
        print('  %-24s %6d bytes' % (os.path.basename(ruta),
                                     os.path.getsize(ruta)))

    # Control: releer lo generado y confirmar que quedó como se pidió
    print()
    problemas = []

    with Image.open(ruta_ico) as ico:
        tamanos = sorted(ico.info.get('sizes', []))
        if tamanos != sorted(TAMANOS_ICO):
            problemas.append('el .ico no trae los tres tamaños: %s' % tamanos)

    for nombre, lado in SALIDAS_PNG:
        with Image.open(os.path.join(ESTATICOS, nombre)) as im:
            if im.size != (lado, lado):
                problemas.append('%s mide %s y debería ser %dx%d'
                                 % (nombre, im.size, lado, lado))

    if problemas:
        print('QUEDO ALGO MAL:')
        for p in problemas:
            print('  - %s' % p)
        return 1

    print('verificado: los cuatro archivos quedaron con las medidas pedidas')
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Genera el favicon a partir del logo.')
    parser.add_argument('--inicial', action='store_true',
                        help='usa la inicial S sobre el verde de la marca en '
                             'lugar del logotipo (se lee en 16 px)')
    ARGUMENTOS = parser.parse_args()
    sys.exit(main())
