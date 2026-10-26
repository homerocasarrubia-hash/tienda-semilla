"""Búsqueda de fotos de producto por código de barras.

Primero se buscan fotos de catálogo (fondo blanco) en supermercados online
que usan VTEX, con su API pública. Si ahí no aparece nada, se prueba en
Open Food Facts. Este módulo solo habla con internet: no toca la base.
"""
import re
import time

import requests

import imagenes

HOSTS_VTEX = (
    'www.carrefour.com.ar',
    'www.jumbo.com.ar',
    'diaonline.supermercadosdia.com.ar',
    'www.vea.com.ar',
    'www.disco.com.ar',
    'www.masonline.com.ar',
)

# Identificarse con un nombre propio es parte de las reglas de Open Food Facts
USER_AGENT = 'SemillaTiendaNatural/1.0 (semilla.tiendanatural@gmail.com)'

ETIQUETA_CATALOGO = 'Catálogo'
ETIQUETA_OFF = 'Open Food Facts'

URL_VTEX = 'https://{host}/api/catalog_system/pub/products/search'
URL_OFF = 'https://world.openfoodfacts.org/api/v2/product/{codigo}.json'

# Cuántas fotos de catálogo alcanzan: más es ruido para quien revisa
MAXIMO_CATALOGO = 4
PAUSA_ENTRE_HOSTS = 0.3
INTERVALO_OFF = 1.0
TIEMPO_ESPERA = (6, 20)

_ID_VTEX = re.compile(r'/arquivos/ids/(\d+)(?:-\d+-\d+)?/')


class Limitador:
    """Deja pasar como mucho una consulta cada `intervalo` segundos."""

    def __init__(self, intervalo, reloj=time.monotonic, dormir=time.sleep):
        self.intervalo = intervalo
        self._reloj = reloj
        self._dormir = dormir
        self._ultima = None

    def esperar(self):
        ahora = self._reloj()
        if self._ultima is not None:
            falta = self.intervalo - (ahora - self._ultima)
            if falta > 0:
                self._dormir(falta)
                ahora = self._reloj()
        self._ultima = ahora


class Resultado:
    def __init__(self, fotos, errores):
        self.fotos = fotos        # [{'url', 'etiqueta', 'fuente'}], mejores primero
        self.errores = errores    # consultas que fallaron (red, 429, 5xx...)

    @property
    def estado(self):
        if self.fotos:
            return 'con_fotos'
        return 'error' if self.errores else 'sin_resultados'


# --- código de barras ----------------------------------------------------

def normalizar_codigo(texto):
    """Deja solo los dígitos y comprueba el dígito verificador (GS1).

    Devuelve el código limpio, '' si estaba vacío, o None si no es válido
    (largo raro o dígito verificador que no cierra: casi siempre un error
    de tipeo).
    """
    digitos = re.sub(r'[\s\-.]', '', str(texto or ''))

    if digitos == '':
        return ''
    if not digitos.isdigit() or len(digitos) not in (8, 12, 13, 14):
        return None

    cuerpo, verificador = digitos[:-1], int(digitos[-1])
    suma = 0
    for posicion, d in enumerate(reversed(cuerpo)):
        suma += int(d) * (3 if posicion % 2 == 0 else 1)

    return digitos if (10 - suma % 10) % 10 == verificador else None


# --- VTEX ----------------------------------------------------------------

def ampliar_vtex(url):
    """/arquivos/ids/123/ -> /arquivos/ids/123-1000-1000/ (pide 1000 px)."""
    return _ID_VTEX.sub(r'/arquivos/ids/\1-1000-1000/', url, count=1)


def _id_de_imagen(url):
    encontrado = _ID_VTEX.search(url)
    return encontrado.group(1) if encontrado else url


def fotos_vtex(codigo, sesion, hosts=HOSTS_VTEX, maximo=MAXIMO_CATALOGO,
               pausa=PAUSA_ENTRE_HOSTS, dormir=time.sleep):
    """Devuelve (fotos, errores)."""
    fotos = []
    vistas = set()
    errores = 0

    for numero, host in enumerate(hosts):
        if len(fotos) >= maximo:
            break
        if numero:
            dormir(pausa)

        try:
            # El código son solo dígitos (ver normalizar_codigo), así que
            # se arma la dirección tal cual la documenta VTEX
            r = sesion.get(URL_VTEX.format(host=host) + '?fq=alternateIds_Ean:' + codigo,
                           timeout=TIEMPO_ESPERA)
        except requests.RequestException:
            errores += 1
            continue

        # VTEX contesta 206 (contenido parcial) en las búsquedas normales
        if r.status_code == 404:
            continue
        if r.status_code not in (200, 206):
            errores += 1
            continue

        try:
            productos = r.json()
        except ValueError:
            errores += 1
            continue

        if not isinstance(productos, list):
            continue

        for producto in productos:
            for item in (producto or {}).get('items') or []:
                # Una ficha puede juntar varios tamaños: solo el del código
                if item.get('ean') and str(item['ean']) != codigo:
                    continue

                imagenes_item = [i for i in (item.get('images') or [])
                                 if i.get('imageUrl')]
                if not imagenes_item:
                    continue

                url = ampliar_vtex(imagenes_item[0]['imageUrl'])
                clave = _id_de_imagen(url)
                if clave in vistas:
                    continue
                vistas.add(clave)
                fotos.append({'url': url, 'etiqueta': ETIQUETA_CATALOGO,
                              'fuente': host})

    return fotos[:maximo], errores


# --- Open Food Facts -----------------------------------------------------

def fotos_off(codigo, sesion, limitador):
    """Devuelve (fotos, errores). Una consulta por segundo como máximo."""
    limitador.esperar()

    try:
        r = sesion.get(URL_OFF.format(codigo=codigo),
                       params={'fields': 'product_name,image_front_url,image_url'},
                       timeout=TIEMPO_ESPERA)
    except requests.RequestException:
        return [], 1

    # Un producto que no está en la base de OFF contesta 404
    if r.status_code == 404:
        return [], 0
    if r.status_code != 200:
        return [], 1

    try:
        producto = r.json().get('product') or {}
    except (ValueError, AttributeError):
        return [], 1

    fotos = []
    for campo in ('image_front_url', 'image_url'):
        url = producto.get(campo)
        if url and imagenes.es_url(url) and url not in [f['url'] for f in fotos]:
            fotos.append({'url': url, 'etiqueta': ETIQUETA_OFF,
                          'fuente': 'openfoodfacts'})

    return fotos[:1], 0


# --- todo junto ----------------------------------------------------------

def nueva_sesion():
    sesion = requests.Session()
    sesion.headers.update({'User-Agent': USER_AGENT, 'Accept': 'application/json'})
    return sesion


def buscar(codigo, sesion=None, limitador_off=None, hosts=HOSTS_VTEX,
           dormir=time.sleep):
    """Catálogo primero; Open Food Facts solo si ahí no apareció nada."""
    sesion = sesion or nueva_sesion()
    limitador_off = limitador_off or Limitador(INTERVALO_OFF)

    fotos, errores = fotos_vtex(codigo, sesion, hosts=hosts, dormir=dormir)

    if not fotos:
        extra, errores_off = fotos_off(codigo, sesion, limitador_off)
        fotos = extra
        errores += errores_off

    return Resultado(fotos, errores)


# --- descarga ------------------------------------------------------------

def descargar(url, sesion=None):
    """Bytes de la imagen, o None si por cualquier motivo no se pudo bajar."""
    if not imagenes.es_url(url):
        return None

    sesion = sesion or nueva_sesion()

    try:
        r = sesion.get(url, timeout=TIEMPO_ESPERA, stream=True,
                       headers={'Accept': 'image/*'})
        try:
            if r.status_code != 200:
                return None

            partes = []
            total = 0
            for trozo in r.iter_content(64 * 1024):
                total += len(trozo)
                if total > imagenes.MAXIMO_BYTES:
                    return None
                partes.append(trozo)
        finally:
            r.close()
    except requests.RequestException:
        return None

    return b''.join(partes) or None
