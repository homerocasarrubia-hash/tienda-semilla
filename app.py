import os
import secrets

from flask import Flask, jsonify, render_template, request

import datos
from admin import bp_admin


def _cargar_env():
    """Lee las variables del archivo .env de esta carpeta, si existe.

    Lo que ya venga definido en el entorno real tiene prioridad; el archivo
    solo completa lo que falte. Así no importa desde qué terminal se levante
    el sitio: la contraseña siempre se encuentra en el mismo lugar.
    """
    ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')

    try:
        # utf-8-sig: el Bloc de notas y PowerShell suelen dejar una marca
        # invisible al principio del archivo, y esto la descarta.
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
        # Por si alguien escribe la clave entre comillas
        valor = valor.strip().strip('"').strip("'")

        if clave and clave not in os.environ:
            os.environ[clave] = valor


_cargar_env()

app = Flask(__name__)

# --- SESIÓN DEL PANEL DE ADMINISTRACIÓN ---
# La clave firma la cookie de sesión. Si no está definida en el entorno se
# genera una al azar: el panel funciona igual, pero cada reinicio del servidor
# cierra la sesión abierta.
app.secret_key = os.environ.get('SECRET_KEY')
if not app.secret_key:
    app.secret_key = secrets.token_hex(32)
    print('AVISO: no hay SECRET_KEY definida en el entorno. Se generó una '
          'temporal, así que vas a tener que entrar de nuevo al panel cada '
          'vez que reinicies el servidor.')

app.register_blueprint(bp_admin)


# --- IMÁGENES DE PRODUCTO ---
# Los productos declaran un archivo en "imagen", pero puede que todavía no
# exista en static/img/. Chequear acá evita pedirle al navegador cientos de
# imágenes inexistentes: la card muestra directamente su placeholder.
# La comprobación vive en datos.py para que el panel también pueda usarla.
@app.context_processor
def utilidades_template():
    return {
        'imagen_existe': datos.imagen_existe,
        'estado_stock': datos.estado_stock,
        # El carrito vive en localStorage y puede tener productos que se
        # agotaron después: necesita esta lista para marcarlos.
        'nombres_sin_stock': datos.nombres_sin_stock(),
    }


@app.route('/')
def inicio():
    info = {
        "nombre": "Semilla Tienda Natural",
        "direccion": "Nuñez del Prado 136, Andalgalá, Catamarca",
        "instagram": "/semillatiendanatural/",
        "email": "semilla.tiendanatural@gmail.com"
    }
    return render_template('inicio.html', datos=info)


@app.route('/buscar')
def buscar():
    q = request.args.get('q', '').lower().strip()
    if len(q) < 1:
        return jsonify([])

    palabras = q.split()

    def coincide(p):
        nombre = p['nombre'].lower()
        # Todas las palabras escritas deben aparecer en algún lugar del nombre
        return all(any(palabra_nombre.startswith(palabra) for palabra_nombre in nombre.split())
                   for palabra in palabras)

    def puntaje(p):
        nombre = p['nombre'].lower()
        if nombre.startswith(q):
            return 0
        elif any(palabra.startswith(q) for palabra in nombre.split()):
            return 1
        elif q in nombre:
            return 2
        else:
            return 3

    resultados = [p for p in datos.cargar() if coincide(p)]
    resultados.sort(key=puntaje)

    return jsonify([
        {"nombre": p["nombre"], "categoria": p["categoria"],
         "stock": datos.estado_stock(p)}
        for p in resultados[:8]
    ])


@app.route('/compras')
def compras():
    busqueda = request.args.get('q', '').lower().strip()
    subcat = request.args.get('subcat', '').strip()
    cat = request.args.get('cat', '').strip()
    productos = datos.cargar()

    if cat == 'Sin TACC':
        # Lo sin TACC está repartido: además de su categoría propia, hay
        # harinas, cervezas y suplementos que lo aclaran en el nombre. Se
        # recorre la lista una sola vez, así no se repite ningún producto
        # y se respeta el orden del catálogo.
        resultados = [p for p in productos
                      if p.get('categoria', '') == cat
                      or 'sin tacc' in p.get('nombre', '').lower()]
        titulo = cat
    elif cat:
        # Filtro exacto por categoría (desde el menú)
        resultados = [p for p in productos if p.get('categoria', '') == cat]
        titulo = cat
    elif subcat:
        # Filtro exacto por subcategoría (desde el menú)
        resultados = [p for p in productos if p.get('subcategoria', '') == subcat]
        titulo = subcat.upper()
    elif busqueda:
        palabras = busqueda.split()
        resultados = [
            p for p in productos
            if all(
                any(palabra_nombre.startswith(palabra) for palabra_nombre in p['nombre'].lower().split())
                or palabra in p['descripcion'].lower()
                or palabra in p['categoria'].lower()
                or palabra in p.get('subcategoria', '').lower()
                for palabra in palabras
            )
        ]
        titulo = busqueda.upper()
    else:
        resultados = productos
        titulo = "Nuestros Productos"

    # Lo agotado va al fondo de la grilla en todas las vistas. sorted() es
    # estable, así que dentro de cada grupo se respeta el orden del catálogo.
    resultados = sorted(resultados, key=datos.sin_stock)

    return render_template('productos.html', productos=resultados, titulo=titulo)


if __name__ == '__main__':
    app.run(debug=True)
