# -*- coding: utf-8 -*-
"""Descarga y aplica las fotos de los productos envasados.

    python scripts/fotos.py
    python scripts/fotos.py --dry-run
    python scripts/fotos.py --solo-categoria "Suplementos"
    python scripts/fotos.py --limite 40

El criterio es deliberadamente conservador: ante la menor duda el producto
queda sin foto. Una card sin foto ya tiene su placeholder y no molesta;
una foto de otra marca publicada en la tienda, sí.

No modifica productos.json, ni app.py, ni las plantillas: lo único que
escribe son archivos nuevos en static/img/ y los dos .txt de este directorio.
"""
import argparse
import io
import os
import re
import sys
import time
import unicodedata
from datetime import datetime

CARPETA = os.path.dirname(os.path.abspath(__file__))
PROYECTO = os.path.dirname(CARPETA)
sys.path.insert(0, PROYECTO)

RUTA_IMAGENES = os.path.join(PROYECTO, 'static', 'img')
RUTA_LOG = os.path.join(CARPETA, 'fotos_log.txt')
RUTA_SIN_FOTO = os.path.join(CARPETA, 'sin_foto.txt')


# =========================================================================
# CONFIGURACIÓN
# =========================================================================

CATEGORIAS = [
    'Suplementos', 'Suplementos Deportivos', 'Aceites', 'Salsas', 'Vinagres',
    'Pastas Untables', 'Granolas', 'Arroces', 'Sin TACC', 'Cervezas',
]

# Marketplaces de terceros: suelen republicar la foto con la marca de agua
# de otra tienda encima.
DOMINIOS_BLOQUEADOS = (
    'mercadolibre', 'mlstatic', 'ebay', 'ebayimg', 'aliexpress', 'alicdn',
    'alibaba', 'pinterest', 'pinimg', 'facebook', 'fbcdn', 'instagram',
    'cdninstagram',
)

LADO_MINIMO = 400
ASPECTO_MINIMO = 0.6
ASPECTO_MAXIMO = 1.7
LADO_MAXIMO_FINAL = 800
CALIDAD_JPG = 82

SEGUNDOS_ENTRE_BUSQUEDAS = 1.0
TIMEOUT = 20
MAXIMO_BYTES = 12 * 1024 * 1024

# Palabras que no aportan identidad al producto
VACIAS = {
    'de', 'del', 'la', 'el', 'los', 'las', 'para', 'con', 'sin', 'y', 'a',
    'al', 'en', 'por', 'tacc', 'marca', 'unidad', 'sabor', 'sabores',
}
UNIDADES = {
    'g', 'gr', 'kg', 'ml', 'lt', 'l', 'cm3', 'caps', 'capsulas', 'comp',
    'comprimidos', 'unidades', 'gomitas', 'doy', 'pack',
}


# =========================================================================
# UTILIDADES
# =========================================================================

def normalizar(texto):
    """minúsculas y sin tildes, para comparar sin sorpresas."""
    texto = unicodedata.normalize('NFKD', str(texto))
    texto = texto.encode('ascii', 'ignore').decode()
    return texto.lower()


def cargar_env():
    """Lee el .env del proyecto. Lo que ya esté en el entorno tiene prioridad.

    Es el mismo criterio que usa app.py, repetido acá a propósito para que el
    script no tenga que importar toda la aplicación solo para leer dos claves.
    """
    ruta = os.path.join(PROYECTO, '.env')
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


class Registro(object):
    """Log a archivo y, lo importante, a consola."""

    def __init__(self, ruta):
        self.ruta = ruta
        self.archivo = open(ruta, 'a', encoding='utf-8')
        self.archivo.write('\n%s\n%s corrida nueva\n%s\n' % (
            '=' * 78, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), '=' * 78))

    def linea(self, texto, mostrar=True):
        self.archivo.write(texto + '\n')
        self.archivo.flush()
        if mostrar:
            print(texto)

    def cerrar(self):
        self.archivo.close()


# =========================================================================
# DATOS DEL PRODUCTO
# =========================================================================

def marca_de(producto):
    """La marca sale de la descripción ("Marca X.") o de la subcategoría.

    Ojo: subcategoria NO siempre es la marca. En "Sin TACC" es el tipo de
    producto (Fideos, Algas), así que la descripción manda.
    """
    m = re.search(r'Marca ([^.]+)\.', producto.get('descripcion', ''))
    if m:
        return m.group(1).strip()

    # Solo sirve como marca en las categorías donde la subcategoría es la marca
    if producto.get('categoria') in ('Suplementos', 'Suplementos Deportivos', 'Cervezas'):
        return (producto.get('subcategoria') or '').strip()

    return ''


def nombre_limpio(producto):
    """El nombre sin el sufijo SIN TACC, para armar la búsqueda."""
    return producto['nombre'].split(' — ')[0].strip()


def palabras_significativas(producto, marca):
    """Palabras del nombre que identifican al producto.

    Se van la marca, las unidades, los números, las preposiciones y todo lo
    de menos de tres letras.
    """
    nombre = re.sub(r'\s+x\s+.*$', '', nombre_limpio(producto))
    tokens = [t for t in re.split(r'[^a-z0-9+]+', normalizar(nombre)) if t]
    tokens_marca = {t for t in re.split(r'[^a-z0-9]+', normalizar(marca)) if t}

    return [t for t in tokens
            if t not in VACIAS
            and t not in UNIDADES
            and t not in tokens_marca
            and not t.isdigit()
            and len(t) >= 3]


def construir_consulta(producto, marca):
    return '%s %s' % (nombre_limpio(producto), marca)


# =========================================================================
# BÚSQUEDA
# =========================================================================

class CuotaAgotada(Exception):
    """La API no acepta más consultas por hoy: seguir no tiene sentido."""


def buscar_imagenes(consulta, api_key, cse_id):
    """Devuelve los candidatos con sus metadatos.

    La API informa ancho, alto, título y dominio, así que los descartes se
    resuelven sin bajar ni un byte de imagen.
    """
    import requests

    respuesta = requests.get(
        'https://www.googleapis.com/customsearch/v1',
        params={
            'key': api_key,
            'cx': cse_id,
            'q': consulta,
            'searchType': 'image',
            'num': 10,
            'safe': 'active',
        },
        timeout=TIMEOUT,
    )

    if respuesta.status_code in (403, 429):
        detalle = ''
        try:
            detalle = respuesta.json().get('error', {}).get('message', '')
        except ValueError:
            pass
        if 'quota' in detalle.lower() or respuesta.status_code == 429:
            raise CuotaAgotada(detalle or 'la API rechazó la consulta por cuota')
        raise RuntimeError('la API respondió %d: %s' % (respuesta.status_code, detalle))

    respuesta.raise_for_status()
    datos = respuesta.json()

    candidatos = []
    for item in datos.get('items', []):
        imagen = item.get('image', {}) or {}
        candidatos.append({
            'url': item.get('link', ''),
            'titulo': item.get('title', '') or '',
            'dominio': item.get('displayLink', '') or '',
            'ancho': int(imagen.get('width') or 0),
            'alto': int(imagen.get('height') or 0),
        })
    return candidatos


# =========================================================================
# CRITERIO DE ACEPTACIÓN
# =========================================================================

def marca_aparece(marca, texto):
    """La marca completa, o todos sus tokens por separado."""
    marca_norm = normalizar(marca).strip()
    texto_norm = normalizar(texto)
    if not marca_norm:
        return False
    if marca_norm in texto_norm:
        return True
    tokens = [t for t in re.split(r'[^a-z0-9]+', marca_norm) if len(t) >= 3]
    return bool(tokens) and all(t in texto_norm for t in tokens)


def evaluar(candidato, marca, significativas):
    """(aceptado, motivo). El motivo explica el descarte en el log."""
    ancho, alto = candidato['ancho'], candidato['alto']

    if ancho < LADO_MINIMO or alto < LADO_MINIMO:
        return False, 'chica (%dx%d, mínimo %d)' % (ancho, alto, LADO_MINIMO)

    if not alto:
        return False, 'sin dimensiones informadas'

    aspecto = ancho / float(alto)
    if not (ASPECTO_MINIMO <= aspecto <= ASPECTO_MAXIMO):
        return False, 'aspecto %.2f fuera de %.1f-%.1f' % (
            aspecto, ASPECTO_MINIMO, ASPECTO_MAXIMO)

    dominio = normalizar(candidato['dominio'])
    for bloqueado in DOMINIOS_BLOQUEADOS:
        if bloqueado in dominio:
            return False, 'marketplace de terceros (%s)' % candidato['dominio']

    archivo = os.path.basename(candidato['url'].split('?')[0])
    if not marca_aparece(marca, candidato['titulo']) and not marca_aparece(marca, archivo):
        return False, 'ni el título ni el archivo mencionan «%s»' % marca

    # Aceptación: la marca tiene que estar en el TÍTULO, no alcanza el archivo
    if not marca_aparece(marca, candidato['titulo']):
        return False, 'la marca solo aparece en el nombre del archivo'

    titulo_norm = normalizar(candidato['titulo'])
    coinciden = [p for p in significativas if p in titulo_norm]
    if len(coinciden) < 2:
        return False, 'el título coincide en %d palabra(s) del producto, hacen falta 2' % len(coinciden)

    return True, 'título coincide en marca y en %s' % ', '.join(coinciden[:4])


# =========================================================================
# DESCARGA Y PROCESAMIENTO
# =========================================================================

def descargar_y_guardar(url, destino):
    """Baja la imagen, la normaliza y la guarda como JPG."""
    import requests
    from PIL import Image

    respuesta = requests.get(url, timeout=TIMEOUT, stream=True,
                             headers={'User-Agent': 'Mozilla/5.0 (fotos.py)'})
    respuesta.raise_for_status()

    tipo = respuesta.headers.get('Content-Type', '')
    if not tipo.startswith('image/'):
        raise ValueError('la respuesta no es una imagen (%s)' % (tipo or 'sin tipo'))

    crudo = io.BytesIO()
    for pedazo in respuesta.iter_content(64 * 1024):
        crudo.write(pedazo)
        if crudo.tell() > MAXIMO_BYTES:
            raise ValueError('la imagen pesa más de %d MB' % (MAXIMO_BYTES // 1024 // 1024))
    crudo.seek(0)

    imagen = Image.open(crudo)
    imagen.load()

    # Los PNG con transparencia van sobre blanco: si no, el alfa se convierte
    # en negro y el packaging queda con bordes sucios.
    if imagen.mode in ('RGBA', 'LA', 'P'):
        imagen = imagen.convert('RGBA')
        fondo = Image.new('RGB', imagen.size, (255, 255, 255))
        fondo.paste(imagen, mask=imagen.split()[-1])
        imagen = fondo
    else:
        imagen = imagen.convert('RGB')

    imagen.thumbnail((LADO_MAXIMO_FINAL, LADO_MAXIMO_FINAL), Image.LANCZOS)

    # Se escribe en un temporal y se renombra: una corrida interrumpida no
    # deja un JPG cortado en static/img/.
    temporal = destino + '.tmp'
    imagen.save(temporal, 'JPEG', quality=CALIDAD_JPG, optimize=True)
    os.replace(temporal, destino)

    return imagen.size


# =========================================================================
# PROGRAMA
# =========================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Descarga y aplica las fotos de los productos envasados.')
    parser.add_argument('--dry-run', action='store_true',
                        help='busca y reporta, pero no escribe nada en static/img/')
    parser.add_argument('--solo-categoria', metavar='CATEGORIA',
                        help='procesa una sola categoría (para probar de a tandas)')
    parser.add_argument('--limite', type=int, default=100, metavar='N',
                        help='cuántos productos buscar como máximo en esta corrida '
                             '(por defecto 100, la cuota diaria gratuita)')
    args = parser.parse_args()

    cargar_env()
    api_key = os.environ.get('GOOGLE_API_KEY', '').strip()
    cse_id = os.environ.get('GOOGLE_CSE_ID', '').strip()

    if not api_key or not cse_id:
        faltan = []
        if not api_key:
            faltan.append('GOOGLE_API_KEY')
        if not cse_id:
            faltan.append('GOOGLE_CSE_ID')
        print("""
No puedo buscar fotos: falta %s.

El script usa la API de Google Custom Search, que necesita dos datos:

  1. GOOGLE_API_KEY — la clave de la API.
     Entrá a  https://console.cloud.google.com/apis/credentials
     Creá un proyecto, activá "Custom Search API" y generá una clave.

  2. GOOGLE_CSE_ID — el id del buscador.
     Entrá a  https://programmablesearchengine.google.com/controlpanel/all
     Creá un buscador, activá "Buscar en toda la web" y "Búsqueda de
     imágenes", y copiá el "ID del motor de búsqueda".

Después agregá las dos líneas al archivo .env de la carpeta del proyecto:

  GOOGLE_API_KEY=tu-clave-aca
  GOOGLE_CSE_ID=tu-id-aca

El plan gratuito permite 100 consultas por día, que es justo el valor por
defecto de --limite. Para hacer más en un día hay que habilitar facturación
en Google Cloud (alrededor de 5 dólares cada 1000 consultas).
""".strip() % ' y '.join(faltan))
        return 1

    try:
        import requests  # noqa: F401
        from PIL import Image  # noqa: F401
    except ImportError as e:
        print('Falta una dependencia (%s).\nInstalalas con:\n\n    '
              'pip install -r requirements.txt\n' % e.name)
        return 1

    import datos

    categorias = CATEGORIAS
    if args.solo_categoria:
        if args.solo_categoria not in CATEGORIAS:
            print('La categoría «%s» no está en el alcance del script.\n'
                  'Las válidas son:\n  - %s'
                  % (args.solo_categoria, '\n  - '.join(CATEGORIAS)))
            return 1
        categorias = [args.solo_categoria]

    if not os.path.isdir(RUTA_IMAGENES):
        os.makedirs(RUTA_IMAGENES)

    productos = [p for p in datos.cargar() if p.get('categoria') in categorias]

    log = Registro(RUTA_LOG)
    log.linea('modo: %s | categorias: %s | limite: %d'
              % ('DRY-RUN (no escribe)' if args.dry_run else 'aplicar',
                 ', '.join(categorias), args.limite))
    log.linea('productos en alcance: %d' % len(productos))
    log.linea('-' * 78)

    aplicadas = []
    sin_foto = []       # (nombre, motivo)
    ya_tenian = 0
    buscados = 0
    corte_por_cuota = False

    for producto in productos:
        nombre = producto['nombre']
        destino = os.path.join(RUTA_IMAGENES, producto.get('imagen', ''))

        # 1. Ya tiene foto: no se toca (así la segunda corrida solo reintenta
        #    los que quedaron sin nada)
        if producto.get('imagen') and os.path.exists(destino):
            ya_tenian += 1
            log.linea('YA TENIA   | %s' % nombre, mostrar=False)
            continue

        if not producto.get('imagen'):
            sin_foto.append((nombre, 'el producto no tiene nombre de archivo cargado'))
            log.linea('SIN CAMPO  | %s' % nombre)
            continue

        # 2. Sin marca no se puede aplicar el filtro más importante
        marca = marca_de(producto)
        if not marca:
            sin_foto.append((nombre, 'no se pudo deducir la marca'))
            log.linea('SIN MARCA  | %s' % nombre)
            continue

        significativas = palabras_significativas(producto, marca)
        if len(significativas) < 2:
            sin_foto.append((nombre, 'el nombre tiene menos de 2 palabras significativas '
                                     '(%s)' % (', '.join(significativas) or 'ninguna')))
            log.linea('NOMBRE CORTO | %s' % nombre)
            continue

        if buscados >= args.limite:
            log.linea('LIMITE     | corte en %d busquedas' % args.limite)
            break

        # 3. Buscar
        consulta = construir_consulta(producto, marca)
        buscados += 1
        try:
            candidatos = buscar_imagenes(consulta, api_key, cse_id)
        except CuotaAgotada as e:
            log.linea('CUOTA      | se agotó la cuota diaria: %s' % e)
            log.linea('             la corrida se detiene acá; volvé a correrlo mañana')
            corte_por_cuota = True
            break
        except Exception as e:
            sin_foto.append((nombre, 'error al buscar: %s' % e))
            log.linea('ERROR      | %s | %s' % (nombre, e))
            time.sleep(SEGUNDOS_ENTRE_BUSQUEDAS)
            continue

        time.sleep(SEGUNDOS_ENTRE_BUSQUEDAS)

        if not candidatos:
            sin_foto.append((nombre, 'la búsqueda no devolvió resultados'))
            log.linea('SIN RESULT | %s' % nombre)
            continue

        # 4. Elegir el primero que califique
        elegido = None
        motivos = []
        for candidato in candidatos:
            acepta, motivo = evaluar(candidato, marca, significativas)
            if acepta:
                elegido = (candidato, motivo)
                break
            motivos.append('%s: %s' % (candidato['dominio'] or '?', motivo))

        if elegido is None:
            resumen = 'ninguno de los %d candidatos calificó' % len(candidatos)
            sin_foto.append((nombre, resumen))
            log.linea('DESCARTADO | %s | %s' % (nombre, resumen))
            for m in motivos[:5]:
                log.linea('             - %s' % m, mostrar=False)
            continue

        candidato, motivo = elegido

        if args.dry_run:
            aplicadas.append(nombre)
            log.linea('APLICARIA  | %s' % nombre)
            log.linea('             %s | %s' % (candidato['dominio'], motivo), mostrar=False)
            continue

        # 5. Bajar y guardar
        try:
            medidas = descargar_y_guardar(candidato['url'], destino)
        except Exception as e:
            sin_foto.append((nombre, 'falló la descarga: %s' % e))
            log.linea('FALLO BAJA | %s | %s' % (nombre, e))
            continue

        aplicadas.append(nombre)
        log.linea('APLICADA   | %s -> %s (%dx%d) desde %s'
                  % (nombre, producto['imagen'], medidas[0], medidas[1],
                     candidato['dominio']))

    # ---------------------------------------------------------------
    # Reporte
    # ---------------------------------------------------------------
    procesados = len(aplicadas) + len(sin_foto)

    log.linea('')
    log.linea('=' * 78)
    log.linea('RESUMEN')
    log.linea('  productos en alcance      : %d' % len(productos))
    log.linea('  ya tenían foto (salteados): %d' % ya_tenian)
    log.linea('  procesados en esta corrida: %d' % procesados)
    log.linea('  búsquedas hechas          : %d' % buscados)
    log.linea('  fotos %-20s: %d' % ('que se aplicarían' if args.dry_run else 'aplicadas',
                                     len(aplicadas)))
    log.linea('  quedaron sin foto         : %d' % len(sin_foto))

    if corte_por_cuota:
        log.linea('')
        log.linea('  ATENCION: la corrida se cortó por cuota agotada.')
        log.linea('  Volvé a correr el script mañana: retoma solo los que faltan.')

    if sin_foto:
        log.linea('')
        log.linea('SIN FOTO (%d):' % len(sin_foto))
        for nombre, motivo in sin_foto:
            log.linea('  - %s' % nombre)
            log.linea('      %s' % motivo)

    with open(RUTA_SIN_FOTO, 'w', encoding='utf-8') as f:
        f.write('Productos que quedaron sin foto\n')
        f.write('%s\n' % datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        f.write('=' * 78 + '\n\n')
        for nombre, motivo in sin_foto:
            f.write('%s\n    %s\n\n' % (nombre, motivo))
        if not sin_foto:
            f.write('(ninguno)\n')

    log.linea('')
    log.linea('log completo : %s' % RUTA_LOG)
    log.linea('sin foto     : %s' % RUTA_SIN_FOTO)
    if args.dry_run:
        log.linea('')
        log.linea('Fue una corrida de prueba: no se escribió ninguna imagen.')

    log.cerrar()
    return 0


if __name__ == '__main__':
    sys.exit(main())
