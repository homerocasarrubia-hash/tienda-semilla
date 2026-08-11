"""Panel de administración del catálogo.

Todas las rutas de este blueprint están protegidas: el chequeo se hace en
before_request, así una ruta nueva queda protegida sola aunque uno se olvide
de ponerle el decorador.
"""
import hmac
import os
import secrets

from flask import (Blueprint, flash, jsonify, redirect, render_template,
                   request, session, url_for)

import datos
import descuentos

bp_admin = Blueprint('admin', __name__, url_prefix='/admin')

# Lo único a lo que se puede llegar sin haber entrado
_SIN_LOGIN = {'admin.login'}


# --- seguridad -----------------------------------------------------------

def token_csrf():
    """Token propio de la sesión, para que nadie pueda mandar formularios
    desde otra página aprovechando que ella dejó la sesión abierta."""
    if 'csrf' not in session:
        session['csrf'] = secrets.token_hex(16)
    return session['csrf']


@bp_admin.before_request
def proteger():
    # 1. Todo lo que modifica datos viaja por POST y tiene que traer el token
    if request.method == 'POST':
        enviado = request.form.get('csrf_token', '')
        if not hmac.compare_digest(enviado, token_csrf()):
            flash('La página estuvo demasiado tiempo abierta y por seguridad '
                  'no se guardó nada. Volvé a intentarlo.', 'error')
            return redirect(url_for('admin.lista') if session.get('admin')
                            else url_for('admin.login'))

    # 2. Salvo el login, todo exige sesión iniciada
    if request.endpoint in _SIN_LOGIN:
        return None

    if not session.get('admin'):
        return redirect(url_for('admin.login'))

    return None


@bp_admin.app_template_filter('pesos')
def filtro_pesos(valor):
    """12500 -> 12.500, con el punto de miles que se usa acá."""
    try:
        return '{:,.0f}'.format(float(valor)).replace(',', '.')
    except (TypeError, ValueError):
        return valor


@bp_admin.context_processor
def variables_comunes():
    return {
        'csrf_token': token_csrf(),
        'todas_las_categorias': datos.categorias(),
        'todas_las_subcategorias': datos.subcategorias(),
        'estados_stock': datos.ESTADOS_STOCK,
        'estado_stock': datos.estado_stock,
        'marcas': datos.MARCAS,
    }


@bp_admin.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('admin'):
        return redirect(url_for('admin.lista'))

    error = None

    if request.method == 'POST':
        contrasena_real = os.environ.get('ADMIN_PASSWORD', '')
        enviada = request.form.get('password', '')

        if not contrasena_real:
            error = ('El panel todavía no tiene contraseña configurada. '
                     'Hay que escribirla en el archivo «.env» que está en la '
                     'carpeta del sitio, en la línea ADMIN_PASSWORD.')
        elif hmac.compare_digest(enviada.encode('utf-8'),
                                 contrasena_real.encode('utf-8')):
            session['admin'] = True
            return redirect(url_for('admin.lista'))
        else:
            error = 'La contraseña no es correcta. Fijate y probá de nuevo.'

    return render_template('admin/login.html', error=error)


@bp_admin.route('/logout', methods=['POST'])
def logout():
    session.clear()
    flash('Cerraste la sesión.', 'ok')
    return redirect(url_for('admin.login'))


# --- listado -------------------------------------------------------------

@bp_admin.route('/')
def lista():
    q = request.args.get('q', '').strip()
    cat = request.args.get('cat', '').strip()
    stock = request.args.get('stock', '').strip()
    marca = request.args.get('marca', '').strip()

    productos = datos.cargar()
    total = len(productos)

    if cat:
        productos = [p for p in productos if p.get('categoria', '') == cat]

    if stock == 'revisar':
        # Lo que hay que mirar: agotado o por agotarse
        productos = [p for p in productos
                     if datos.estado_stock(p) in ('sin_stock', 'ultimas')]
    elif stock:
        productos = [p for p in productos if datos.estado_stock(p) == stock]

    if marca in dict(datos.MARCAS):
        productos = [p for p in productos if p.get(marca)]

    if q:
        busqueda = q.lower()
        productos = [
            p for p in productos
            if busqueda in p.get('nombre', '').lower()
            or busqueda in p.get('descripcion', '').lower()
        ]

    todos = datos.cargar()
    sin_precio = sum(1 for p in todos if not _tiene_precio(p))
    sin_foto = sum(1 for p in todos if not datos.imagen_existe(p.get('imagen')))
    agotados = sum(1 for p in todos if datos.estado_stock(p) == 'sin_stock')
    en_oferta = sum(1 for p in todos if p.get('es_oferta'))
    novedades = sum(1 for p in todos if p.get('es_novedad'))

    return render_template('admin/lista.html',
                           productos=productos,
                           total=total,
                           sin_precio=sin_precio,
                           sin_foto=sin_foto,
                           agotados=agotados,
                           en_oferta=en_oferta,
                           novedades=novedades,
                           q=q,
                           cat=cat,
                           stock=stock,
                           marca=marca)


@bp_admin.route('/productos/<int:id_producto>/stock', methods=['POST'])
def cambiar_stock(id_producto):
    """Cambio de estado desde el listado, sin entrar a editar."""
    producto = datos.obtener(id_producto)
    nuevo = request.form.get('stock', '').strip()

    if producto is None:
        mensaje, categoria = 'Ese producto ya no está en el catálogo.', 'error'
    elif nuevo not in dict(datos.ESTADOS_STOCK):
        mensaje, categoria = 'Ese estado de stock no existe.', 'error'
    else:
        producto['stock'] = nuevo
        datos.actualizar(id_producto, producto)
        etiqueta = dict(datos.ESTADOS_STOCK)[nuevo]
        mensaje = '«%s» quedó como: %s.' % (producto['nombre'], etiqueta)
        categoria = 'ok'

    if request.headers.get('X-Requested-With') == 'fetch':
        return jsonify({'ok': categoria == 'ok', 'mensaje': mensaje})

    flash(mensaje, categoria)
    return redirect(url_for('admin.lista',
                            q=request.form.get('q', ''),
                            cat=request.form.get('cat', ''),
                            stock=request.form.get('filtro_stock', '')))


def _tiene_precio(p):
    if 'precio_100g' in p:
        return bool(p.get('precio_100g')) or bool(p.get('precio_kg'))
    return bool(p.get('precio'))


@bp_admin.route('/productos/<int:id_producto>/marca', methods=['POST'])
def cambiar_marca(id_producto):
    """Prende o apaga oferta / novedad desde el listado."""
    campo = request.form.get('campo', '').strip()
    valor = request.form.get('valor', '') in ('1', 'true', 'on')
    etiquetas = dict(datos.MARCAS)

    producto = datos.obtener(id_producto)

    if producto is None:
        mensaje, categoria = 'Ese producto ya no está en el catálogo.', 'error'
    elif campo not in etiquetas:
        mensaje, categoria = 'Esa marca no existe.', 'error'
    else:
        datos.cambiar_marca(id_producto, campo, valor)
        mensaje = '«%s»: %s %s.' % (producto['nombre'], etiquetas[campo].lower(),
                                    'activada' if valor else 'desactivada')
        categoria = 'ok'

    if request.headers.get('X-Requested-With') == 'fetch':
        return jsonify({'ok': categoria == 'ok', 'mensaje': mensaje})

    flash(mensaje, categoria)
    return redirect(url_for('admin.lista',
                            q=request.form.get('q', ''),
                            cat=request.form.get('cat', ''),
                            stock=request.form.get('filtro_stock', ''),
                            marca=request.form.get('filtro_marca', '')))


# --- alta y edición ------------------------------------------------------

@bp_admin.route('/productos/nuevo', methods=['GET', 'POST'])
def nuevo():
    if request.method == 'POST':
        producto, errores = _leer_formulario()

        if not errores and datos.existe_nombre(producto['nombre'],
                                               producto['categoria']):
            errores.append(
                'Ya hay un producto que se llama «%s» en la categoría «%s». '
                'Si querés cambiarle el precio o la descripción, buscalo en '
                'la lista y tocá Editar.'
                % (producto['nombre'], producto['categoria']))

        if errores:
            return render_template('admin/formulario.html',
                                   producto=producto, errores=errores,
                                   es_nuevo=True)

        creado = datos.crear(producto)
        flash('Se agregó «%s» al catálogo.' % creado['nombre'], 'ok')
        return redirect(url_for('admin.lista', q=creado['nombre']))

    return render_template('admin/formulario.html',
                           producto=None, errores=[], es_nuevo=True)


@bp_admin.route('/productos/<int:id_producto>/editar', methods=['GET', 'POST'])
def editar(id_producto):
    producto = datos.obtener(id_producto)

    if producto is None:
        flash('Ese producto ya no está en el catálogo.', 'error')
        return redirect(url_for('admin.lista'))

    if request.method == 'POST':
        editado, errores = _leer_formulario()
        editado['id'] = id_producto

        if not errores and datos.existe_nombre(editado['nombre'],
                                               editado['categoria'],
                                               excepto_id=id_producto):
            errores.append(
                'Ya hay otro producto que se llama «%s» en la categoría «%s».'
                % (editado['nombre'], editado['categoria']))

        if errores:
            return render_template('admin/formulario.html',
                                   producto=editado, errores=errores,
                                   es_nuevo=False)

        datos.actualizar(id_producto, editado)
        flash('Se guardaron los cambios de «%s».' % editado['nombre'], 'ok')
        return redirect(url_for('admin.lista'))

    return render_template('admin/formulario.html',
                           producto=producto, errores=[], es_nuevo=False)


@bp_admin.route('/productos/<int:id_producto>/eliminar', methods=['GET', 'POST'])
def eliminar(id_producto):
    producto = datos.obtener(id_producto)

    if producto is None:
        flash('Ese producto ya no está en el catálogo.', 'error')
        return redirect(url_for('admin.lista'))

    if request.method == 'POST':
        datos.eliminar(id_producto)
        flash('Se eliminó «%s» del catálogo.' % producto['nombre'], 'ok')
        return redirect(url_for('admin.lista'))

    return render_template('admin/eliminar.html', producto=producto)


# --- descuentos ----------------------------------------------------------

@bp_admin.route('/descuentos', methods=['GET', 'POST'])
def lista_descuentos():
    errores = []
    codigo = ''
    porcentaje_texto = ''

    if request.method == 'POST':
        codigo, porcentaje, errores = descuentos.revisar(
            request.form.get('codigo'), request.form.get('porcentaje'))
        porcentaje_texto = request.form.get('porcentaje', '')

        if not errores:
            creado = descuentos.crear(codigo, porcentaje)
            flash('Se creó el código «%s» con %d%% de descuento.'
                  % (creado['codigo'], creado['porcentaje']), 'ok')
            return redirect(url_for('admin.lista_descuentos'))

    return render_template('admin/descuentos.html',
                           descuentos=descuentos.listar(),
                           errores=errores,
                           codigo=codigo,
                           porcentaje=porcentaje_texto)


@bp_admin.route('/descuentos/<int:id_descuento>/activo', methods=['POST'])
def cambiar_activo_descuento(id_descuento):
    valor = request.form.get('valor', '') in ('1', 'true', 'on')
    encontrado = descuentos.obtener(id_descuento)

    if encontrado is None:
        mensaje, categoria = 'Ese código ya no existe.', 'error'
    else:
        descuentos.cambiar_activo(id_descuento, valor)
        mensaje = '«%s» quedó %s.' % (encontrado['codigo'],
                                      'activo' if valor else 'desactivado')
        categoria = 'ok'

    if request.headers.get('X-Requested-With') == 'fetch':
        return jsonify({'ok': categoria == 'ok', 'mensaje': mensaje})

    flash(mensaje, categoria)
    return redirect(url_for('admin.lista_descuentos'))


@bp_admin.route('/descuentos/<int:id_descuento>/eliminar', methods=['GET', 'POST'])
def eliminar_descuento(id_descuento):
    encontrado = descuentos.obtener(id_descuento)

    if encontrado is None:
        flash('Ese código ya no existe.', 'error')
        return redirect(url_for('admin.lista_descuentos'))

    if request.method == 'POST':
        descuentos.eliminar(id_descuento)
        flash('Se eliminó el código «%s».' % encontrado['codigo'], 'ok')
        return redirect(url_for('admin.lista_descuentos'))

    return render_template('admin/eliminar_descuento.html', descuento=encontrado)


# --- precios en lote -----------------------------------------------------

@bp_admin.route('/precios', methods=['GET', 'POST'])
def precios():
    cat = request.args.get('cat', '').strip()

    if request.method == 'POST':
        cat = request.form.get('cat', '').strip()
        cambios, errores = _leer_precios_en_lote()

        if errores:
            for e in errores:
                flash(e, 'error')
            return redirect(url_for('admin.precios', cat=cat))

        modificados = datos.actualizar_precios(cambios)

        if modificados == 0:
            flash('No cambiaste ningún precio.', 'ok')
        elif modificados == 1:
            flash('Se actualizó el precio de 1 producto.', 'ok')
        else:
            flash('Se actualizaron los precios de %d productos.' % modificados, 'ok')

        return redirect(url_for('admin.precios', cat=cat))

    productos = datos.cargar()
    if cat:
        productos = [p for p in productos if p.get('categoria', '') == cat]

    return render_template('admin/precios.html', productos=productos, cat=cat)


def _leer_precios_en_lote():
    """Lee los campos del formulario de precios.

    Cada input se llama "precio_100g-12", donde 12 es el id del producto.
    """
    cambios = {}
    errores = []
    por_id = {p['id']: p for p in datos.cargar()}

    for campo, valor in request.form.items():
        if '-' not in campo:
            continue
        clave, _, id_texto = campo.rpartition('-')
        if clave not in ('precio_100g', 'precio_kg', 'precio'):
            continue

        try:
            id_producto = int(id_texto)
        except ValueError:
            continue

        producto = por_id.get(id_producto)
        if producto is None or clave not in producto:
            continue

        numero, error = _leer_precio(valor, _NOMBRE_PRECIO[clave],
                                     producto.get('nombre', ''))
        if error:
            errores.append(error)
        else:
            cambios.setdefault(id_producto, {})[clave] = numero

    return cambios, errores


# --- lectura y validación del formulario ---------------------------------

_NOMBRE_PRECIO = {
    'precio_100g': 'el precio por 100 gramos',
    'precio_kg': 'el precio por kilo',
    'precio': 'el precio',
}


def _leer_precio(texto, que_precio, nombre_producto=''):
    """Convierte lo que se escribió en un número.

    Acepta que le pongan el signo $, espacios y puntos de miles. Vacío
    significa "todavía no tiene precio", que en el sitio se muestra como
    "Precio a confirmar".
    """
    texto = (texto or '').strip()

    if texto == '':
        return 0, None

    limpio = (texto.replace('$', '').replace(' ', '')
              .replace('.', '').replace(',', '.'))

    donde = (' de «%s»' % nombre_producto) if nombre_producto else ''

    try:
        numero = float(limpio)
    except ValueError:
        return None, ('Revisá %s%s: escribí solo números, sin letras. '
                      'Por ejemplo: 2500' % (que_precio, donde))

    if numero < 0:
        return None, 'Revisá %s%s: no puede ser un número negativo.' % (que_precio, donde)

    if numero > 100_000_000:
        return None, ('Revisá %s%s: ese número es altísimo, fijate si no se '
                      'te coló un dígito de más.' % (que_precio, donde))

    # Los precios del catálogo son enteros; solo se guarda con decimales si
    # de verdad los tiene.
    return (int(numero) if numero == int(numero) else round(numero, 2)), None


def _leer_formulario():
    """Arma el producto a partir del formulario y junta los errores."""
    f = request.form
    errores = []

    nombre = f.get('nombre', '').strip()
    descripcion = f.get('descripcion', '').strip()
    imagen = f.get('imagen', '').strip()
    subcategoria = f.get('subcategoria', '').strip()
    tipo = f.get('tipo', 'granel')

    categoria = f.get('categoria', '').strip()
    if categoria == '__nueva__':
        categoria = f.get('categoria_nueva', '').strip()

    if not nombre:
        errores.append('Poné el nombre del producto.')

    if not categoria:
        errores.append('Elegí una categoría de la lista, o escribí una nueva.')

    # El buscador del sitio lee la descripción de todos los productos, así que
    # siempre se guarda como texto aunque quede vacía.
    producto = {
        'nombre': nombre,
        'descripcion': descripcion,
    }

    if tipo == 'unidad':
        precio, error = _leer_precio(f.get('precio'), _NOMBRE_PRECIO['precio'])
        if error:
            errores.append(error)
        producto['precio'] = precio if precio is not None else 0
    else:
        p100, error100 = _leer_precio(f.get('precio_100g'), _NOMBRE_PRECIO['precio_100g'])
        pkg, errorkg = _leer_precio(f.get('precio_kg'), _NOMBRE_PRECIO['precio_kg'])
        if error100:
            errores.append(error100)
        if errorkg:
            errores.append(errorkg)
        producto['precio_100g'] = p100 if p100 is not None else 0
        producto['precio_kg'] = pkg if pkg is not None else 0

    producto['categoria'] = categoria
    if subcategoria:
        producto['subcategoria'] = subcategoria
    producto['imagen'] = imagen

    stock = f.get('stock', '').strip()
    producto['stock'] = stock if stock in dict(datos.ESTADOS_STOCK) else 'disponible'

    # Las casillas solo llegan en el formulario cuando están tildadas
    producto['es_oferta'] = 'es_oferta' in f
    producto['es_novedad'] = 'es_novedad' in f

    return producto, errores
