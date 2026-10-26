# -*- coding: utf-8 -*-
"""Pruebas del buscador de fotos por código de barras.

    python probar_fotos_ean.py

Corre sobre una base SQLite temporal y con internet simulado: no toca la
base real, ni Cloudinary, ni los supermercados.
"""
import importlib.util
import io
import os
import sys
import tempfile

CARPETA = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, CARPETA)

# Antes de importar nada del proyecto: base temporal y sin credenciales
_tmp = tempfile.mkdtemp()
os.environ['DATABASE_URL'] = 'sqlite:///' + os.path.join(_tmp, 'prueba.db').replace('\\', '/')
os.environ['SECRET_KEY'] = 'prueba'
os.environ['ADMIN_PASSWORD'] = 'prueba'
os.environ['CLOUDINARY_URL'] = ''

import requests  # noqa: E402
from sqlalchemy import event  # noqa: E402

import buscador_fotos as bf  # noqa: E402
import datos  # noqa: E402
import db  # noqa: E402
import fotos_sugeridas as fs  # noqa: E402
import imagenes  # noqa: E402

fallas = []
total = 0


def comprobar(condicion, que):
    global total
    total += 1
    if not condicion:
        fallas.append(que)
        print('  FALLA: ' + que)


# --- base temporal -------------------------------------------------------
motor = db.motor()
assert str(motor.url).startswith('sqlite'), 'la prueba no puede tocar la base real'


@event.listens_for(motor, 'connect')
def _funciones(conexion, _):
    conexion.create_function('btrim', 1, lambda s: s.strip() if s else s)


db.tabla().create(motor)
fs.asegurar()


def producto(nombre, **extra):
    base = {'nombre': nombre, 'descripcion': '', 'categoria': 'Aceites',
            'precio': 100, 'stock': 'disponible'}
    base.update(extra)
    return datos.crear(base)


# --- respuestas simuladas -------------------------------------------------

class Resp:
    def __init__(self, estado=200, cuerpo=None, trozos=None):
        self.status_code = estado
        self._cuerpo = cuerpo
        self._trozos = trozos or []

    def json(self):
        if isinstance(self._cuerpo, Exception):
            raise self._cuerpo
        return self._cuerpo

    def iter_content(self, n):
        return iter(self._trozos)

    def close(self):
        pass


class Sesion:
    """Contesta según el host de la dirección pedida."""

    def __init__(self, respuestas):
        self.respuestas = respuestas
        self.pedidos = []
        self.headers = {}

    def get(self, url, **kw):
        self.pedidos.append(url)
        for clave, valor in self.respuestas.items():
            if clave in url:
                if isinstance(valor, Exception):
                    raise valor
                return valor
        return Resp(404)


def ficha(*ids, ean='7790895000782'):
    return [{'items': [{'ean': ean, 'images': [
        {'imageUrl': 'https://x.vteximg.com.br/arquivos/ids/%s/foto.jpg?v=1' % i}]}
        for i in ids]}]


SIN_PAUSA = lambda s: None  # noqa: E731
EAN = '7790895000782'

# =========================================================================
print('código de barras')
comprobar(bf.normalizar_codigo(EAN) == EAN, 'EAN-13 válido')
comprobar(bf.normalizar_codigo(' 7790895 000782 ') == EAN, 'espacios se descartan')
comprobar(bf.normalizar_codigo('7790895-000782') == EAN, 'guiones se descartan')
comprobar(bf.normalizar_codigo('7790895000783') is None, 'dígito verificador mal')
comprobar(bf.normalizar_codigo('abc') is None, 'letras')
comprobar(bf.normalizar_codigo('12345') is None, 'largo raro')
comprobar(bf.normalizar_codigo('') == '' and bf.normalizar_codigo(None) == '', 'vacío')
comprobar(bf.normalizar_codigo('96385074') == '96385074', 'EAN-8 válido')
comprobar(bf.normalizar_codigo('036000291452') == '036000291452', 'UPC-12 válido')

print('tamaño de la foto')
original = 'https://carrefourar.vteximg.com.br/arquivos/ids/332206/7790895000782_E01.jpg?v=638211437573270000'
comprobar(bf.ampliar_vtex(original) ==
          'https://carrefourar.vteximg.com.br/arquivos/ids/332206-1000-1000/7790895000782_E01.jpg?v=638211437573270000',
          'pide 1000 px')
comprobar(bf.ampliar_vtex(bf.ampliar_vtex(original)).count('-1000-1000') == 1,
          'no duplica el tamaño')
comprobar(bf.ampliar_vtex('https://otro.com/foto.jpg') == 'https://otro.com/foto.jpg',
          'otra dirección queda igual')

print('VTEX')
s = Sesion({
    'carrefour': Resp(206, ficha(111)),            # 206 = respuesta normal de VTEX
    'jumbo': Resp(200, []),                        # sin resultados
    'diaonline': Resp(500),                        # error del sitio
    'vea': requests.ConnectionError('caído'),      # sin red
    'disco': Resp(200, ficha(111)),                # misma foto que Carrefour
    'masonline': Resp(200, ficha(222)),
})
fotos, errores = bf.fotos_vtex(EAN, s, dormir=SIN_PAUSA)
comprobar([f['url'].split('/ids/')[1].split('/')[0] for f in fotos] == ['111-1000-1000', '222-1000-1000'],
          'fotos ampliadas y sin repetir: %r' % [f['url'] for f in fotos])
comprobar(all(f['etiqueta'] == 'Catálogo' for f in fotos), 'etiqueta Catálogo')
comprobar(errores == 2, 'cuenta los errores (500 y red): %d' % errores)
comprobar(all(('?fq=alternateIds_Ean:' + EAN) in u for u in s.pedidos), 'dirección de la API')
comprobar(len(s.pedidos) == 6, 'consulta los 6 hosts')

s = Sesion({h: Resp(200, ficha(i)) for i, h in enumerate(
    ['carrefour', 'jumbo', 'diaonline', 'vea', 'disco', 'masonline'], 10)})
fotos, _ = bf.fotos_vtex(EAN, s, dormir=SIN_PAUSA)
comprobar(len(fotos) == bf.MAXIMO_CATALOGO and len(s.pedidos) == bf.MAXIMO_CATALOGO,
          'corta al llegar al máximo')

s = Sesion({'carrefour': Resp(200, ficha(5, ean='7790000000000'))})
comprobar(bf.fotos_vtex(EAN, s, hosts=bf.HOSTS_VTEX[:1], dormir=SIN_PAUSA)[0] == [],
          'ignora otros tamaños de la misma ficha')
s = Sesion({'carrefour': Resp(200, cuerpo=ValueError())})
comprobar(bf.fotos_vtex(EAN, s, hosts=bf.HOSTS_VTEX[:1], dormir=SIN_PAUSA) == ([], 1),
          'respuesta que no es JSON = error')

print('Open Food Facts y orden de búsqueda')
OFF_OK = Resp(200, {'status': 1, 'product': {'image_front_url': 'https://off.org/front.400.jpg',
                                              'image_url': 'https://off.org/front.400.jpg'}})
lim = bf.Limitador(0)

s = Sesion({'catalog_system': Resp(200, ficha(7)), 'openfoodfacts': OFF_OK})
r = bf.buscar(EAN, sesion=s, limitador_off=lim, dormir=SIN_PAUSA)
comprobar(r.estado == 'con_fotos' and not any('openfoodfacts' in u for u in s.pedidos),
          'si hay catálogo no consulta Open Food Facts')

s = Sesion({'catalog_system': Resp(200, []), 'openfoodfacts': OFF_OK})
r = bf.buscar(EAN, sesion=s, limitador_off=lim, dormir=SIN_PAUSA)
comprobar(r.estado == 'con_fotos' and r.fotos[0]['etiqueta'] == 'Open Food Facts'
          and len(r.fotos) == 1, 'sin catálogo cae a Open Food Facts (sin repetir la misma foto)')

s = Sesion({'catalog_system': Resp(200, []), 'openfoodfacts': Resp(404)})
comprobar(bf.buscar(EAN, sesion=s, limitador_off=lim, dormir=SIN_PAUSA).estado == 'sin_resultados',
          'ningún lado = sin_resultados')

s = Sesion({'catalog_system': Resp(200, []), 'openfoodfacts': Resp(200, {'status': 0})})
comprobar(bf.buscar(EAN, sesion=s, limitador_off=lim, dormir=SIN_PAUSA).estado == 'sin_resultados',
          'OFF sin foto = sin_resultados')

s = Sesion({'catalog_system': requests.ConnectionError(), 'openfoodfacts': requests.Timeout()})
comprobar(bf.buscar(EAN, sesion=s, limitador_off=lim, dormir=SIN_PAUSA).estado == 'error',
          'todo cae por la red = error (se reintenta, no se da por buscado)')

s = Sesion({'catalog_system': Resp(500), 'openfoodfacts': Resp(429)})
comprobar(bf.buscar(EAN, sesion=s, limitador_off=lim, dormir=SIN_PAUSA).estado == 'error',
          '500 y 429 = error')

print('un pedido por segundo a Open Food Facts')
reloj = [100.0]
esperas = []
lim = bf.Limitador(1.0, reloj=lambda: reloj[0],
                   dormir=lambda t: (esperas.append(t), reloj.__setitem__(0, reloj[0] + t)))
lim.esperar()
reloj[0] += 0.25
lim.esperar()
reloj[0] += 5
lim.esperar()
comprobar(len(esperas) == 1 and abs(esperas[0] - 0.75) < 1e-9,
          'espera lo que falta y no espera de más: %r' % esperas)

comprobar(bf.USER_AGENT.startswith('SemillaTiendaNatural/')
          and bf.nueva_sesion().headers['User-Agent'] == bf.USER_AGENT,
          'User-Agent propio')

print('descarga')
comprobar(bf.descargar('ftp://x/y.jpg') is None and bf.descargar('') is None, 'solo http(s)')
comprobar(bf.descargar('https://x/y.jpg', Sesion({'x/y': Resp(200, trozos=[b'ab', b'cd'])})) == b'abcd',
          'junta los trozos')
comprobar(bf.descargar('https://x/y.jpg', Sesion({'x/y': Resp(403)})) is None, '403 = None')
comprobar(bf.descargar('https://x/y.jpg', Sesion({'x/y': requests.ConnectionError()})) is None,
          'sin red = None')
grande = [b'0' * (1024 * 1024)] * (imagenes.MAXIMO_BYTES // (1024 * 1024) + 2)
comprobar(bf.descargar('https://x/y.jpg', Sesion({'x/y': Resp(200, trozos=grande)})) is None,
          'archivo gigante = None')

# =========================================================================
print('base de datos')
a = producto('Aceite de oliva')                                   # con código, sin foto
b = producto('Almendras sueltas', categoria='Frutos', precio=None, precio_100g=1, precio_kg=2)  # suelto
c = producto('Aceite con foto', imagen='https://res.cloudinary.com/x/image/upload/v1/semilla/productos/z.jpg')
d = producto('Aceite de coco', imagen='viejo.jpg')                # nombre viejo sin archivo = sin foto
e = producto('Aceite de girasol')                                 # con código, sin foto

for i, cod in ((a['id'], EAN), (c['id'], '96385074'), (d['id'], '036000291452'), (e['id'], '7791234567895')):
    fs.guardar_codigo(i, cod)
comprobar(fs.codigo_de(a['id']) == EAN and fs.codigo_de(b['id']) == '', 'guarda y lee el código')

todos = [p['id'] for p in fs.para_buscar()]
comprobar(todos == [a['id'], d['id'], e['id']],
          'busca solo con código y sin foto; los sueltos se saltean: %r' % todos)

fotos_a = [{'url': 'https://off.org/a.jpg', 'etiqueta': 'Open Food Facts', 'fuente': 'off'},
           {'url': 'https://x/ids/1-1000-1000/a.jpg', 'etiqueta': 'Catálogo', 'fuente': 'jumbo'}]
n = fs.registrar_busqueda(a['id'], EAN, bf.Resultado(fotos_a, 0))
comprobar(n == 2, 'guarda las fotos')
comprobar([p['id'] for p in fs.para_buscar()] == [d['id'], e['id']], 'retoma: lo ya buscado no se repite')

fs.registrar_busqueda(d['id'], '036000291452', bf.Resultado([], 0))
comprobar([p['id'] for p in fs.para_buscar()] == [e['id']], 'sin_resultados tampoco se repite')

fs.registrar_busqueda(e['id'], '7791234567895', bf.Resultado([], 1))
comprobar([p['id'] for p in fs.para_buscar()] == [e['id']], 'un error de red sí se reintenta')
comprobar(len(fs.para_buscar(rehacer=True)) == 3, 'rehacer incluye todo')
comprobar([p['id'] for p in fs.para_buscar(solo_id=a['id'], rehacer=True)] == [a['id']], 'un producto solo')

grupos = fs.pendientes()
comprobar(len(grupos) == 1 and grupos[0]['producto']['id'] == a['id'], 'un producto por revisar')
comprobar([f['etiqueta'] for f in grupos[0]['fotos']] == ['Catálogo', 'Open Food Facts'],
          'catálogo primero aunque se haya guardado después')
res = fs.resumen()
comprobar(res['fotos_por_revisar'] == 2 and res['productos_por_revisar'] == 1
          and res['sin_foto_con_codigo'] == 3 and res['sin_buscar'] == 1, 'resumen: %r' % res)

# Volver a buscar reemplaza lo pendiente
fs.registrar_busqueda(a['id'], EAN, bf.Resultado(fotos_a[1:], 0))
comprobar(len(fs.pendientes()[0]['fotos']) == 1, 'rebuscar reemplaza las pendientes')
fs.registrar_busqueda(a['id'], EAN, bf.Resultado(fotos_a, 0))

print('Usar / Ninguna sirve')
from PIL import Image  # noqa: E402
jpg = io.BytesIO()
Image.new('RGB', (1000, 1000), 'white').save(jpg, 'JPEG')
JPG = jpg.getvalue()
subidas = []
borradas = []
imagenes_borrar = imagenes.borrar
imagenes.borrar = lambda url: borradas.append(url) or True


def subir_falso(crudo):
    subidas.append(len(crudo))
    return 'https://res.cloudinary.com/x/image/upload/v1/semilla/productos/nueva.jpg'


ids = [f['id'] for f in fs.pendientes()[0]['fotos']]
ok, msg = fs.usar(ids[0], descargar=lambda u: JPG, subir=subir_falso)
comprobar(ok and 'ya tiene su foto' in msg, 'Usar responde bien')
comprobar(datos.obtener(a['id'])['imagen'].endswith('nueva.jpg') and len(subidas) == 1,
          'descargó, subió y guardó la dirección nueva')
comprobar(fs.pendientes() == [], 'el resto de las sugerencias del producto quedan descartadas')
ok, msg = fs.usar(ids[1], descargar=lambda u: JPG, subir=subir_falso)
comprobar(not ok and 'ya se revisó' in msg and len(subidas) == 1, 'doble clic: no sube dos veces')
ok, _ = fs.usar(999999)
comprobar(not ok, 'sugerencia que no existe')
comprobar(a['id'] not in [p['id'] for p in fs.para_buscar(rehacer=True)], 'con foto ya no se busca')

# Fallbacks silenciosos: siempre ok=True y queda la dirección original
casos = (
    ('no se pudo bajar', lambda u: None, subir_falso),
    ('sin red y sin servicio de fotos', lambda u: None, None),
    ('la foto no sirve', lambda u: b'no es una foto', None),
    ('sin credenciales del servicio de fotos', lambda u: JPG, None),
    ('falla el servicio de fotos', lambda u: JPG, lambda c: 1 / 0),
)
for numero, (caso, descargar, subir) in enumerate(casos):
    url = 'https://x/ids/9-1000-1000/%d.jpg' % numero
    fs.registrar_busqueda(e['id'], '7791234567895', bf.Resultado(
        [{'url': url, 'etiqueta': 'Catálogo', 'fuente': 'x'}], 0))
    sid = fs.pendientes()[0]['fotos'][0]['id']
    # subir=None usa el imagenes.subir real: sin CLOUDINARY_URL falla solo
    ok, msg = fs.usar(sid, descargar=descargar, subir=subir)
    imagen = datos.obtener(e['id'])['imagen']
    comprobar(ok and imagen == url and 'rror' not in msg,
              '%s: usa la dirección original sin error (%r)' % (caso, imagen))
    datos.actualizar(e['id'], dict(datos.obtener(e['id']), imagen=None))

# Reemplazar una foto del servicio borra la anterior
fs.registrar_busqueda(c['id'], '96385074', bf.Resultado(
    [{'url': 'https://x/otra.jpg', 'etiqueta': 'Catálogo', 'fuente': 'x'}], 0))
fs.usar(fs.pendientes()[0]['fotos'][0]['id'], descargar=lambda u: JPG, subir=subir_falso)
comprobar(borradas == ['https://res.cloudinary.com/x/image/upload/v1/semilla/productos/z.jpg'],
          'reemplazar borra la foto anterior del servicio: %r' % borradas)

# Ninguna sirve
fs.registrar_busqueda(e['id'], '7791234567895', bf.Resultado(fotos_a, 0))
comprobar(fs.descartar_producto(e['id']) == 2 and fs.pendientes() == [], 'Ninguna sirve')
fs.registrar_busqueda(e['id'], '7791234567895', bf.Resultado(fotos_a, 0))
comprobar(fs.pendientes() == [], 'lo descartado no vuelve a sugerirse')

# Cambiar el código reinicia la búsqueda
fs.guardar_codigo(e['id'], '7790895000782')
comprobar(e['id'] in [p['id'] for p in fs.para_buscar()], 'código nuevo = se vuelve a buscar')
comprobar(fs.guardar_codigo(e['id'], '7790895000782') is False, 'mismo código = sin cambios')

# =========================================================================
print('panel')
import app as aplicacion  # noqa: E402

cliente = aplicacion.app.test_client()
with cliente.session_transaction() as sesion:
    sesion['admin'] = True
    sesion['csrf'] = 'tok'

comprobar(cliente.get('/admin/fotos').status_code == 200, 'Fotos abre (vacío)')
fs.registrar_busqueda(e['id'], '7790895000782', bf.Resultado(
    [{'url': 'https://x/ids/2-1000-1000/a.jpg', 'etiqueta': 'Catálogo', 'fuente': 'x'},
     {'url': 'https://off.org/b.jpg', 'etiqueta': 'Open Food Facts', 'fuente': 'off'}], 0))
html = cliente.get('/admin/fotos').get_data(as_text=True)
comprobar('Aceite de girasol' in html and 'Catálogo' in html and 'Open Food Facts' in html
          and html.count('>Usar<') == 2 and 'Ninguna sirve' in html, 'Fotos muestra las sugerencias')
comprobar(html.index('Catálogo') < html.index('Open Food Facts'), 'catálogo se ve primero')

otro = aplicacion.app.test_client()
comprobar(otro.get('/admin/fotos').status_code == 302 and
          otro.post('/admin/fotos/1/usar', data={}).status_code == 302, 'sin sesión no entra')

sid = fs.pendientes()[0]['fotos'][0]['id']
antes = datos.obtener(e['id']).get('imagen')
cliente.post('/admin/fotos/%d/usar' % sid, data={})
comprobar(datos.obtener(e['id']).get('imagen') == antes, 'sin token CSRF no hace nada')

bf_descargar, imagenes_subir = bf.descargar, imagenes.subir
bf.descargar = lambda u, sesion=None: JPG
imagenes.subir = subir_falso
r = cliente.post('/admin/fotos/%d/usar' % sid, data={'csrf_token': 'tok'},
                 headers={'X-Requested-With': 'fetch'})
bf.descargar, imagenes.subir = bf_descargar, imagenes_subir
comprobar(r.status_code == 200 and r.get_json()['ok'] and
          datos.obtener(e['id'])['imagen'].endswith('nueva.jpg'), 'Usar por fetch')

fs.registrar_busqueda(e['id'], '7790895000782', bf.Resultado(
    [{'url': 'https://x/ids/3/a.jpg', 'etiqueta': 'Catálogo', 'fuente': 'x'}], 0))
comprobar(len(fs.pendientes()) == 1, 'hay algo para descartar')
r = cliente.post('/admin/fotos/producto/%d/ninguna' % e['id'], data={'csrf_token': 'tok'})
comprobar(r.status_code == 302 and fs.pendientes() == [], 'Ninguna sirve sin JS')

comprobar(cliente.get('/admin/fotos/codigos').status_code == 200, 'abre Códigos')
html = cliente.get('/admin/fotos/codigos?todos=1').get_data(as_text=True)
comprobar('name="codigo-%d"' % a['id'] in html and 'name="codigo-%d"' % b['id'] in html, 'Códigos lista productos')

r = cliente.post('/admin/fotos/codigos', data={
    'csrf_token': 'tok', 'todos': '1',
    'codigo-%d' % b['id']: '1234', 'codigo-%d' % a['id']: '7790895000783'})
html = r.get_data(as_text=True)
comprobar(r.status_code == 200 and 'no parece correcto' in html and 'value="1234"' in html,
          'código mal escrito: avisa y conserva lo tipeado')
comprobar(fs.codigo_de(b['id']) == '', 'con un error no se guarda nada')

r = cliente.post('/admin/fotos/codigos', data={
    'csrf_token': 'tok', 'todos': '1', 'codigo-%d' % b['id']: '7790895 000782',
    'codigo-%d' % a['id']: ''})
comprobar(r.status_code == 302 and fs.codigo_de(b['id']) == EAN and fs.codigo_de(a['id']) == '',
          'guarda en lote, limpia espacios y borra los vaciados')

print('formulario de producto')
html = cliente.get('/admin/productos/%d/editar' % b['id']).get_data(as_text=True)
comprobar('name="codigo_barras"' in html and 'value="%s"' % EAN in html, 'el formulario muestra el código')
html = cliente.get('/admin/productos/nuevo').get_data(as_text=True)
comprobar('name="codigo_barras"' in html, 'el alta tiene el campo')

datos_form = {'csrf_token': 'tok', 'nombre': 'Aceite de lino', 'categoria': 'Aceites',
              'tipo': 'unidad', 'precio': '100', 'stock': 'disponible'}
r = cliente.post('/admin/productos/nuevo', data=dict(datos_form, codigo_barras='123'))
comprobar(r.status_code == 200 and 'código de barras no parece correcto' in r.get_data(as_text=True)
          and 'value="123"' in r.get_data(as_text=True), 'alta con código inválido no se guarda')
comprobar(not datos.existe_nombre('Aceite de lino', 'Aceites'), 'el producto no se creó')
r = cliente.post('/admin/productos/nuevo', data=dict(datos_form, codigo_barras='7790895000782'))
nuevo = [p for p in datos.cargar() if p['nombre'] == 'Aceite de lino'][0]
comprobar(r.status_code == 302 and fs.codigo_de(nuevo['id']) == EAN, 'alta con código válido')

r = cliente.post('/admin/productos/nuevo', data=dict(datos_form, nombre='Sin código', codigo_barras=''))
sin = [p for p in datos.cargar() if p['nombre'] == 'Sin código'][0]
comprobar(fs.codigo_de(sin['id']) == '', 'alta sin código (suelto)')

r = cliente.post('/admin/productos/%d/editar' % sin['id'],
                 data=dict(datos_form, nombre='Sin código', codigo_barras='96385074'))
comprobar(fs.codigo_de(sin['id']) == '96385074', 'editar agrega el código')
r = cliente.post('/admin/productos/%d/editar' % sin['id'],
                 data=dict(datos_form, nombre='Sin código', codigo_barras=''))
comprobar(fs.codigo_de(sin['id']) == '', 'editar puede quitar el código')

fs.registrar_busqueda(nuevo['id'], EAN, bf.Resultado(fotos_a, 0))
cliente.post('/admin/productos/%d/eliminar' % nuevo['id'], data={'csrf_token': 'tok'})
comprobar(fs.codigo_de(nuevo['id']) == '' and nuevo['id'] not in [g['producto']['id'] for g in fs.pendientes()]
          and nuevo['id'] not in fs.estados_de_busqueda(), 'eliminar el producto limpia sus datos')

print('la tienda pública sigue igual')
comprobar(cliente.get('/compras').status_code == 200 and cliente.get('/').status_code == 200,
          'tienda y catálogo abren')
cols = {c.name for c in db.tabla().columns}
comprobar('codigo_barras' not in cols, 'la tabla de productos no cambió')

# =========================================================================
print('script de línea de comandos')
spec = importlib.util.spec_from_file_location(
    'buscar_fotos_cli', os.path.join(CARPETA, 'scripts', 'buscar_fotos.py'))
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)

lote = [producto('Lote %d' % i) for i in range(4)]
for i, p in enumerate(lote):
    fs.guardar_codigo(p['id'], ['7790895000782', '96385074', '036000291452', '7791234567895'][i])
for p in fs.para_buscar():                      # dejar solo el lote
    if not p['nombre'].startswith('Lote'):
        fs.registrar_busqueda(p['id'], p['codigo'], bf.Resultado([], 0))

llamadas = []
buscar_original = bf.buscar


def buscar_cortado(codigo, **kw):
    llamadas.append(codigo)
    if len(llamadas) == 3:
        raise KeyboardInterrupt
    return bf.Resultado([{'url': 'https://x/%s.jpg' % codigo, 'etiqueta': 'Catálogo', 'fuente': 'x'}], 0)


bf.buscar = buscar_cortado
sys.argv = ['buscar_fotos.py']
real = sys.stdout
sys.stdout = salida = io.StringIO()
codigo_salida = cli.main()
sys.stdout = real
comprobar(codigo_salida == 0 and 'Cortado' in salida.getvalue(), 'Ctrl+C termina prolijo')
comprobar(len(fs.para_buscar()) == 2, 'quedaron guardados los 2 primeros')

llamadas.clear()
bf.buscar = lambda codigo, **kw: (llamadas.append(codigo), bf.Resultado([], 0))[1]
sys.stdout = io.StringIO()
cli.main()
sys.stdout = real
comprobar(llamadas == ['036000291452', '7791234567895'], 'al retomar sigue desde donde quedó: %r' % llamadas)
comprobar(fs.para_buscar() == [], 'al terminar no queda nada pendiente')

sys.argv = ['buscar_fotos.py', '--lista']
sys.stdout = salida = io.StringIO()
cli.main()
sys.stdout = real
comprobar('No hay nada para buscar' in salida.getvalue(), 'sin pendientes lo dice')
bf.buscar = buscar_original

# =========================================================================
print('búsqueda por nombre')
comprobar(bf.coincide('Aceite de Oliva Zuelo 500cc', 'Zuelo Aceite de oliva extra virgen 500 cc'),
          'se parece (tildes y orden aparte)')
comprobar(bf.coincide('Té Verde', 'TÉ VERDE Taragüi x 20'), 'tildes y mayúsculas')
comprobar(not bf.coincide('Aceite de Oliva Zuelo', 'Aceite de girasol Cocinero'),
          'otro aceite no cuenta')
comprobar(not bf.coincide('Almohadita Frutilla', 'Frutilla congelada'), 'una sola palabra no alcanza')
comprobar(not bf.coincide('', 'algo') and not bf.coincide('de la', 'algo'), 'nombre vacío o sin palabras')


def ficha_nombre(titulo, marca, id_imagen):
    return [{'productName': titulo, 'brand': marca, 'items': [{'images': [
        {'imageUrl': 'https://x.vteximg.com.br/arquivos/ids/%s/foto.jpg?v=1' % id_imagen}]}]}]


s = Sesion({
    'carrefour': Resp(206, ficha_nombre('Aceite de oliva extra virgen 500 cc', 'Zuelo', 31)),
    'jumbo': Resp(200, ficha_nombre('Aceite de girasol', 'Cocinero', 32)),     # otro producto
    'diaonline': Resp(200, ficha_nombre('Aceite oliva Zuelo', '', 33)),
})
fotos, errores = bf.fotos_vtex_nombre('Aceite de Oliva Zuelo', s, hosts=bf.HOSTS_VTEX[:3], dormir=SIN_PAUSA)
comprobar(len(fotos) == 2 and errores == 0 and all('-1000-1000' in f['url'] for f in fotos),
          'descarta el que no se parece y amplía: %r' % fotos)
comprobar('carrefour' in fotos[0]['fuente'] and 'Aceite de oliva' in fotos[0]['fuente'],
          'guarda de dónde y con qué título (para revisar)')
comprobar(all('?ft=Aceite%20de%20Oliva%20Zuelo&' in u for u in s.pedidos), 'texto codificado en la dirección')

OFF_TEXTO = Resp(200, {'products': [
    {'product_name': 'Fideos', 'brands': 'Otra', 'image_front_url': 'https://off.org/mal.jpg'},
    {'product_name': 'Aceite de oliva', 'brands': 'Zuelo', 'image_front_url': 'https://off.org/bien.jpg'}]})
s = Sesion({'catalog_system': Resp(200, []), 'search.pl': OFF_TEXTO})
r = bf.buscar_por_nombre('Aceite de Oliva Zuelo', sesion=s, limitador_off=bf.Limitador(0), dormir=SIN_PAUSA)
comprobar(r.estado == 'con_fotos' and r.fotos[0]['url'] == 'https://off.org/bien.jpg'
          and r.fotos[0]['etiqueta'] == 'Open Food Facts', 'sin catálogo cae a Open Food Facts y elige el que se parece')

s = Sesion({'catalog_system': Resp(200, []), 'search.pl': Resp(200, {'products': []})})
comprobar(bf.buscar_por_nombre('Té rojo', sesion=s, limitador_off=bf.Limitador(0), dormir=SIN_PAUSA).estado == 'sin_resultados',
          'nada parecido = sin_resultados')
s = Sesion({'catalog_system': Resp(500), 'search.pl': Resp(503)})
comprobar(bf.buscar_por_nombre('Té rojo', sesion=s, limitador_off=bf.Limitador(0), dormir=SIN_PAUSA).estado == 'error',
          'caídas = error, se reintenta')
comprobar(bf.INTERVALO_OFF_TEXTO >= 6, 'la búsqueda por texto de OFF va despacio')

print('qué se busca por nombre')
u1 = producto('Mermelada de durazno', categoria='Dulces')                 # unidad, sin código
g1 = producto('Mix suelto', categoria='Frutos', precio=None, precio_100g=5, precio_kg=50)  # granel
u2 = producto('Dulce de leche', categoria='Dulces', imagen='https://res.cloudinary.com/x/a.jpg')  # con foto
ids = [p['id'] for p in fs.para_buscar()]
comprobar(u1['id'] in ids, 'unidad sin código se busca por nombre')
comprobar(g1['id'] not in ids and u2['id'] not in ids, 'suelto y con foto se saltean')
comprobar(u1['id'] not in [p['id'] for p in fs.para_buscar(por_nombre=False)], '--solo-codigos lo saca')
item = [p for p in fs.para_buscar() if p['id'] == u1['id']][0]
comprobar(item['codigo'] == '' and item['nombre'] == 'Mermelada de durazno', 'sin código viene vacío')

fs.registrar_busqueda(u1['id'], '', bf.Resultado(
    [{'url': 'https://x/ids/77-1000-1000/m.jpg', 'etiqueta': 'Catálogo', 'fuente': 'jumbo: Mermelada Durazno'}], 0))
comprobar(u1['id'] not in [p['id'] for p in fs.para_buscar()], 'lo buscado por nombre no se repite')
grupo = [g for g in fs.pendientes() if g['producto']['id'] == u1['id']][0]
comprobar(grupo['codigo'] == '' and grupo['fotos'][0]['fuente'] == 'jumbo: Mermelada Durazno',
          'queda para revisar con su título')
html = cliente.get('/admin/fotos').get_data(as_text=True)
comprobar('buscada por nombre' in html and 'jumbo: Mermelada Durazno' in html, 'el panel lo muestra')
fs.guardar_codigo(u1['id'], '7790895000782')
comprobar(u1['id'] in [p['id'] for p in fs.para_buscar()], 'si después le ponés código, se vuelve a buscar')

# El script usa el nombre cuando no hay código
resto = [p for p in fs.para_buscar() if p['codigo'] == '' ]
for p in fs.para_buscar():
    fs.registrar_busqueda(p['id'], p['codigo'], bf.Resultado([], 0))
fs.guardar_codigo(u1['id'], '')
usados = []
bf.buscar_por_nombre = lambda nombre, **kw: (usados.append(nombre), bf.Resultado([], 0))[1]
bf.buscar = lambda codigo, **kw: (usados.append('codigo ' + codigo), bf.Resultado([], 0))[1]
sys.argv = ['buscar_fotos.py']
sys.stdout = io.StringIO()
cli.main()
sys.stdout = real
comprobar(usados == ['Mermelada de durazno'], 'el script busca por nombre al que no tiene código: %r' % usados)
bf.buscar = buscar_original


imagenes.borrar = imagenes_borrar
print()
if fallas:
    print('%d de %d comprobaciones FALLARON' % (len(fallas), total))
    sys.exit(1)
print('%d comprobaciones, todas bien' % total)
