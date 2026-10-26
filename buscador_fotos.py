"""Búsqueda de fotos de producto por código de barras.

Primero se buscan fotos de catálogo (fondo blanco) en supermercados online
que usan VTEX, con su API pública. Si ahí no aparece nada, se prueba en
Open Food Facts. Este módulo solo habla con internet: no toca la base.
"""
import re
import time
import unicodedata
import xml.etree.ElementTree as ET
from urllib.parse import quote

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
ETIQUETA_BIOSALUD = 'Biosalud'
# Las que van primero en el panel (fotos de catálogo / del proveedor)
ETIQUETAS_PRIORITARIAS = (ETIQUETA_CATALOGO, ETIQUETA_BIOSALUD)

# Biosalud (distribuidora mayorista, proveedor de la tienda) no deja usar su
# buscador interno (su robots.txt lo bloquea), pero sí publica un sitemap con
# el título y la foto de cada producto: se lee una vez y se busca ahí.
URL_SITEMAP_BIOSALUD = 'https://bio-salud.com.ar/sitemap.xml'

URL_VTEX = 'https://{host}/api/catalog_system/pub/products/search'
URL_OFF = 'https://world.openfoodfacts.org/api/v2/product/{codigo}.json'

# Cuántas fotos de catálogo alcanzan: más es ruido para quien revisa
MAXIMO_CATALOGO = 4
PAUSA_ENTRE_HOSTS = 0.3
INTERVALO_OFF = 1.0
# La búsqueda por texto de Open Food Facts tiene un límite más estricto
# (unas 10 por minuto): se la trata con mucha más calma.
INTERVALO_OFF_TEXTO = 7.0
URL_OFF_TEXTO = 'https://world.openfoodfacts.org/cgi/search.pl'
PARECIDO_MINIMO = 0.6
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


# --- búsqueda por nombre -------------------------------------------------

_SOBRAN = {'con', 'sin', 'del', 'las', 'los', 'una', 'uno', 'por', 'para',
           'las', 'que', 'mas'}


def _palabras(texto):
    sin_tildes = unicodedata.normalize('NFKD', str(texto or ''))
    sin_tildes = ''.join(c for c in sin_tildes if not unicodedata.combining(c))
    return {w for w in re.findall(r'[a-z0-9]+', sin_tildes.lower())
            if len(w) >= 3 and w not in _SOBRAN}


def _parecido(nombre, titulo):
    """De 0 a 1: qué parte de las palabras del nombre aparece en el título.
    Devuelve 0 si no alcanza lo mínimo para considerarlo el mismo producto."""
    buscadas = _palabras(nombre)
    if not buscadas:
        return 0.0
    encontradas = buscadas & _palabras(titulo)
    if len(buscadas) >= 2 and len(encontradas) < 2:
        return 0.0
    return len(encontradas) / len(buscadas)


def coincide(nombre, titulo, minimo=PARECIDO_MINIMO):
    """¿El título que devolvió el sitio se parece al nombre del producto?

    Se pide que aparezca al menos el 60% de las palabras del nombre (y al
    menos dos si el nombre tiene dos o más): mejor una foto de menos que la
    de otro producto.
    """
    return _parecido(nombre, titulo) >= minimo


def fotos_vtex_nombre(nombre, sesion, hosts=HOSTS_VTEX, maximo=MAXIMO_CATALOGO,
                      pausa=PAUSA_ENTRE_HOSTS, dormir=time.sleep):
    """Texto libre en cada supermercado. Devuelve (fotos, errores)."""
    fotos = []
    vistas = set()
    errores = 0

    for numero, host in enumerate(hosts):
        if len(fotos) >= maximo:
            break
        if numero:
            dormir(pausa)

        try:
            r = sesion.get(URL_VTEX.format(host=host) + '?ft=' + quote(nombre.strip())
                           + '&_from=0&_to=5', timeout=TIEMPO_ESPERA)
        except requests.RequestException:
            errores += 1
            continue

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

        # De cada supermercado, el primer resultado que de verdad se parezca
        for producto in productos:
            producto = producto or {}
            titulo = '%s %s' % (producto.get('brand') or '', producto.get('productName') or '')
            if not coincide(nombre, titulo):
                continue

            url = None
            for item in producto.get('items') or []:
                imagenes_item = [i for i in (item.get('images') or []) if i.get('imageUrl')]
                if imagenes_item:
                    url = ampliar_vtex(imagenes_item[0]['imageUrl'])
                    break
            if not url or _id_de_imagen(url) in vistas:
                continue

            vistas.add(_id_de_imagen(url))
            fotos.append({'url': url, 'etiqueta': ETIQUETA_CATALOGO,
                          'fuente': '%s: %s' % (host, (producto.get('productName') or '').strip())})
            break

    return fotos[:maximo], errores


def fotos_off_nombre(nombre, sesion, limitador):
    """Búsqueda por texto en Open Food Facts. Devuelve (fotos, errores)."""
    limitador.esperar()

    try:
        r = sesion.get(URL_OFF_TEXTO + '?search_simple=1&action=process&json=1&page_size=8'
                       '&fields=product_name,brands,image_front_url&search_terms='
                       + quote(nombre.strip()), timeout=TIEMPO_ESPERA)
    except requests.RequestException:
        return [], 1

    if r.status_code != 200:
        return [], 1

    try:
        productos = r.json().get('products') or []
    except (ValueError, AttributeError):
        return [], 1

    for producto in productos:
        titulo = '%s %s' % (producto.get('brands') or '', producto.get('product_name') or '')
        url = producto.get('image_front_url')
        if url and imagenes.es_url(url) and coincide(nombre, titulo):
            return [{'url': url, 'etiqueta': ETIQUETA_OFF,
                     'fuente': (producto.get('product_name') or '').strip()}], 0

    return [], 0


_indice_biosalud = None


def cargar_indice_biosalud(sesion, forzar=False):
    """Lee el sitemap de Biosalud (una sola vez por corrida).

    Devuelve (lista de {'titulo', 'imagen', 'pagina'}, errores).
    """
    global _indice_biosalud
    if _indice_biosalud is not None and not forzar:
        return _indice_biosalud, 0

    try:
        r = sesion.get(URL_SITEMAP_BIOSALUD, timeout=TIEMPO_ESPERA)
        if r.status_code != 200:
            return [], 1
        raiz = ET.fromstring(r.content)
    except (requests.RequestException, ET.ParseError, AttributeError, TypeError):
        return [], 1

    indice = []
    for entrada in raiz.iter():
        if not entrada.tag.endswith('}url') and entrada.tag != 'url':
            continue
        pagina = imagen = titulo = None
        for hijo in entrada.iter():
            etiqueta = hijo.tag.split('}')[-1]
            texto = (hijo.text or '').strip()
            if etiqueta == 'loc' and hijo is not entrada and pagina is None:
                pagina = texto            # la primera <loc> es la de la página
            elif etiqueta == 'loc' and pagina is not None and not imagen:
                imagen = texto            # la siguiente, dentro de image:image
            elif etiqueta == 'title':
                titulo = texto
        if imagen and imagenes.es_url(imagen) and titulo:
            indice.append({'titulo': titulo, 'imagen': imagen, 'pagina': pagina})

    _indice_biosalud = indice
    return indice, 0


def fotos_biosalud(nombre, sesion, maximo=2):
    """Productos de Biosalud que se parecen al nombre. Devuelve (fotos, errores)."""
    indice, errores = cargar_indice_biosalud(sesion)

    candidatos = []
    for producto in indice:
        puntaje = _parecido(nombre, producto['titulo'])
        if puntaje >= PARECIDO_MINIMO:
            candidatos.append((puntaje, producto))
    candidatos.sort(key=lambda c: -c[0])

    # Solo los que empatan con el mejor: si uno encaja perfecto, no se
    # sugiere además otro sabor o presentación de la misma marca.
    if candidatos:
        mejor = candidatos[0][0]
        candidatos = [c for c in candidatos if c[0] >= mejor - 1e-9]

    return [{'url': p['imagen'], 'etiqueta': ETIQUETA_BIOSALUD,
             'fuente': p['titulo']} for _, p in candidatos[:maximo]], errores


def buscar_por_nombre(nombre, sesion=None, limitador_off=None, hosts=HOSTS_VTEX,
                      dormir=time.sleep):
    """Igual que buscar(), pero con el nombre del producto en vez del código."""
    sesion = sesion or nueva_sesion()
    limitador_off = limitador_off or Limitador(INTERVALO_OFF_TEXTO)

    # Primero el proveedor de la tienda, después los supermercados
    fotos, errores = fotos_biosalud(nombre, sesion)

    if not fotos:
        fotos, errores_vtex = fotos_vtex_nombre(nombre, sesion, hosts=hosts, dormir=dormir)
        errores += errores_vtex

    if not fotos:
        extra, errores_off = fotos_off_nombre(nombre, sesion, limitador_off)
        fotos = extra
        errores += errores_off

    return Resultado(fotos, errores)


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
