"""Fotos de producto: procesamiento y almacenamiento externo.

En Render el disco es efímero: lo que se guarde en static/img/ desaparece
en el próximo reinicio. Por eso las fotos van a Cloudinary y en la base
queda la URL completa.

El procesamiento (achicar, aplanar la transparencia, pasar a JPG) vive acá
y lo usan tanto el panel como scripts/fotos.py, para que haya una sola
implementación y no dos que se desincronicen.
"""
import io
import os
import re
import uuid

LADO_MAXIMO = 800
# Todas las fotos quedan cuadradas, sobre fondo blanco y con el producto
# centrado: así la tienda se ve pareja aunque vengan de distintas fuentes.
MARGEN = 0.06              # espacio blanco alrededor, como fracción del lado
AMPLIAR_MAXIMO = 2.0       # no se estira una foto chica más que esto
UMBRAL_BLANCO = 24         # cuánto se tiene que apartar del blanco para ser "producto"
CALIDAD = 82
MAXIMO_BYTES = 12 * 1024 * 1024
CARPETA_REMOTA = 'semilla/productos'


class ErrorDeImagen(Exception):
    """Algo del archivo que mandó el usuario no sirve. El mensaje es para él."""


class FaltaConfiguracion(RuntimeError):
    """No hay credenciales del servicio de almacenamiento."""


AYUDA = """
No puedo subir la foto: falta la variable CLOUDINARY_URL.

Las fotos no se pueden guardar en el disco del servidor porque Render lo
borra en cada reinicio, así que van a Cloudinary.

  1. Creá una cuenta gratis en  https://cloudinary.com/users/register_free
     (no pide tarjeta).
  2. En el panel, arriba de todo, aparece "API Environment variable" con
     un valor que empieza con cloudinary://
  3. Copiá esa línea entera al archivo .env de la carpeta del proyecto:

        CLOUDINARY_URL=cloudinary://clave:secreto@nombre-de-tu-cuenta

  4. En Render, la misma variable va en Environment.

El plan gratuito alcanza de sobra para las fotos de todo el catálogo.
""".strip()


def hay_servicio():
    return bool(os.environ.get('CLOUDINARY_URL', '').strip())


# --- procesamiento -------------------------------------------------------

def procesar(crudo):
    """Bytes de cualquier formato -> bytes de un JPG listo para publicar.

    Achica al lado máximo, aplana la transparencia sobre blanco y respeta
    la orientación que las cámaras de celular guardan en el EXIF (sin eso,
    las fotos verticales se publican acostadas).
    """
    from PIL import Image, ImageOps, UnidentifiedImageError

    if not crudo:
        raise ErrorDeImagen('No llegó ninguna foto.')

    if len(crudo) > MAXIMO_BYTES:
        raise ErrorDeImagen(
            'La foto pesa más de %d MB. Probá con una más liviana.'
            % (MAXIMO_BYTES // 1024 // 1024))

    try:
        imagen = Image.open(io.BytesIO(crudo))
        imagen.load()
    except (UnidentifiedImageError, OSError, ValueError):
        raise ErrorDeImagen('Ese archivo no parece ser una foto. '
                            'Tiene que ser una imagen (JPG, PNG, etc.).')

    # Las fotos de celular vienen derechas solo si se respeta el EXIF
    try:
        imagen = ImageOps.exif_transpose(imagen)
    except Exception:
        pass

    if imagen.mode in ('RGBA', 'LA', 'P'):
        imagen = imagen.convert('RGBA')
        fondo = Image.new('RGB', imagen.size, (255, 255, 255))
        fondo.paste(imagen, mask=imagen.split()[-1])
        imagen = fondo
    else:
        imagen = imagen.convert('RGB')

    imagen = _centrar_en_cuadrado(imagen)

    salida = io.BytesIO()
    imagen.save(salida, 'JPEG', quality=CALIDAD, optimize=True)
    return salida.getvalue()


def _centrar_en_cuadrado(imagen):
    """Recorta el borde blanco sobrante y centra el producto en un cuadrado blanco."""
    from PIL import Image, ImageChops

    blanco = Image.new('RGB', imagen.size, (255, 255, 255))
    diferencia = ImageChops.difference(imagen, blanco).convert('L')
    mascara = diferencia.point(lambda v: 255 if v > UMBRAL_BLANCO else 0)
    caja = mascara.getbbox()

    ancho, alto = imagen.size
    # Si no hay nada que se distinga del blanco, o el "producto" es una
    # mancha mínima, no se recorta: mejor dejar la foto entera.
    if caja and (caja[2] - caja[0]) * (caja[3] - caja[1]) >= 0.02 * ancho * alto:
        imagen = imagen.crop(caja)

    util = int(LADO_MAXIMO * (1 - 2 * MARGEN))
    ancho, alto = imagen.size
    escala = min(util / ancho, util / alto, AMPLIAR_MAXIMO)
    nuevo = (max(1, round(ancho * escala)), max(1, round(alto * escala)))
    if nuevo != imagen.size:
        imagen = imagen.resize(nuevo, Image.LANCZOS)

    lienzo = Image.new('RGB', (LADO_MAXIMO, LADO_MAXIMO), (255, 255, 255))
    lienzo.paste(imagen, ((LADO_MAXIMO - nuevo[0]) // 2, (LADO_MAXIMO - nuevo[1]) // 2))
    return lienzo


def guardar_en_disco(crudo, destino):
    """Procesa y escribe a un archivo. Lo usa scripts/fotos.py en local."""
    listo = procesar(crudo)
    temporal = destino + '.tmp'
    with open(temporal, 'wb') as f:
        f.write(listo)
    os.replace(temporal, destino)

    from PIL import Image
    with Image.open(destino) as im:
        return im.size


# --- almacenamiento externo ---------------------------------------------

def _configurar():
    import cloudinary

    if not hay_servicio():
        raise FaltaConfiguracion(AYUDA)

    # cloudinary lee CLOUDINARY_URL del entorno por su cuenta
    cloudinary.config(secure=True)
    return cloudinary


def subir(crudo):
    """Procesa y sube. Devuelve la URL pública de la foto.

    El nombre remoto es un identificador al azar: así reemplazar la foto de
    un producto nunca pisa la de otro ni depende del nombre del archivo que
    haya elegido el celular.
    """
    import cloudinary.uploader

    listo = procesar(crudo)
    _configurar()

    respuesta = cloudinary.uploader.upload(
        io.BytesIO(listo),
        folder=CARPETA_REMOTA,
        public_id=uuid.uuid4().hex,
        resource_type='image',
        format='jpg',
    )

    url = respuesta.get('secure_url') or respuesta.get('url')
    if not url:
        raise ErrorDeImagen('El servicio de fotos no devolvió una dirección.')

    return url


def identificador_remoto(url):
    """De la URL de Cloudinary saca el nombre con el que está guardada.

    https://res.cloudinary.com/xxx/image/upload/v123/semilla/productos/ab12.jpg
    -> semilla/productos/ab12
    """
    if not url or CARPETA_REMOTA not in str(url):
        return None

    encontrado = re.search(r'/upload/(?:v\d+/)?(.+?)(?:\.[a-zA-Z0-9]+)?$', str(url))
    return encontrado.group(1) if encontrado else None


def borrar(url):
    """Borra la foto anterior. Si falla no pasa nada: queda un huérfano."""
    import cloudinary.uploader

    identificador = identificador_remoto(url)
    if not identificador:
        return False

    try:
        _configurar()
        # invalidate purga además la copia que el CDN tenga cacheada. Sin
        # esto, una foto borrada se sigue sirviendo un rato desde el borde.
        cloudinary.uploader.destroy(identificador, invalidate=True)
        return True
    except Exception:
        return False


def es_url(valor):
    return bool(valor) and str(valor).strip().lower().startswith(('http://', 'https://'))
