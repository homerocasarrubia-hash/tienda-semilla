/* =========================================================================
   PANEL — solo lo imprescindible del formulario de producto:
   mostrar los campos de precio que correspondan y el nombre de categoría
   nueva cuando hace falta.
   ========================================================================= */
(function () {
    'use strict';

    function mostrar(elemento, visible) {
        if (elemento) elemento.hidden = !visible;
    }

    function iniciarTipoDePrecio() {
        var granel = document.getElementById('campos-granel');
        var unidad = document.getElementById('campos-unidad');
        var radios = document.querySelectorAll('input[name="tipo"]');
        if (!granel || !unidad || !radios.length) return;

        function actualizar() {
            var elegido = document.querySelector('input[name="tipo"]:checked');
            var esGranel = !elegido || elegido.value === 'granel';
            mostrar(granel, esGranel);
            mostrar(unidad, !esGranel);
        }

        radios.forEach(function (r) {
            r.addEventListener('change', actualizar);
        });

        actualizar();
    }

    function iniciarCategoriaNueva() {
        var select = document.getElementById('select-categoria');
        var campo = document.getElementById('campo-categoria-nueva');
        if (!select || !campo) return;

        function actualizar() {
            var esNueva = select.value === '__nueva__';
            mostrar(campo, esNueva);
            if (esNueva) campo.querySelector('input').focus();
        }

        select.addEventListener('change', actualizar);
        // Sin 'change' inicial: si vuelve del servidor con error, el campo ya
        // trae su valor y no hay que robarle el foco.
        mostrar(campo, select.value === '__nueva__');
    }

    /* Cambio de estado desde el listado ----------------------------------
       El formulario de cada fila funciona solo con su botón Guardar. Si hay
       JS, se envía al elegir y no se recarga la página: es lo que más se
       toca y recargar 400 filas cada vez sería insoportable. */

    function iniciarEstadoEnLinea() {
        var formularios = document.querySelectorAll('.form-stock');
        if (!formularios.length) return;

        formularios.forEach(function (form) {
            var select = form.querySelector('.select-stock');
            var boton = form.querySelector('.btn-guardar-stock');
            if (!select) return;

            // Con JS el botón sobra
            if (boton) boton.hidden = true;

            var anterior = select.value;

            select.addEventListener('change', function () {
                var elegido = select.value;
                var datos = new FormData(form);
                select.disabled = true;

                fetch(form.action, {
                    method: 'POST',
                    body: datos,
                    headers: { 'X-Requested-With': 'fetch' },
                })
                    .then(function (r) { return r.json(); })
                    .then(function (respuesta) {
                        if (!respuesta.ok) throw new Error(respuesta.mensaje);
                        anterior = elegido;
                        select.className = 'select-stock estado-' + elegido;
                        marcarGuardado(form);
                    })
                    .catch(function (e) {
                        select.value = anterior;
                        alert('No se pudo guardar el cambio. ' +
                              'Probá de nuevo o recargá la página.\n\n' + e.message);
                    })
                    .then(function () {
                        select.disabled = false;
                    });
            });
        });
    }

    function marcarGuardado(form) {
        var aviso = form.querySelector('.stock-guardado');
        if (!aviso) {
            aviso = document.createElement('span');
            aviso.className = 'stock-guardado';
            form.appendChild(aviso);
        }
        aviso.textContent = 'Guardado';
        aviso.classList.remove('apagando');
        // Se deja ver un momento y se desvanece
        window.setTimeout(function () {
            aviso.classList.add('apagando');
        }, 1200);
    }

    /* Oferta y novedad desde el listado, mismo patrón que el estado ------- */

    function iniciarMarcasEnLinea() {
        var formularios = document.querySelectorAll('.form-marca');
        if (!formularios.length) return;

        formularios.forEach(function (form) {
            var casilla = form.querySelector('.check-marca');
            var boton = form.querySelector('.btn-guardar-marca');
            if (!casilla) return;

            if (boton) boton.hidden = true;

            var anterior = casilla.checked;

            casilla.addEventListener('change', function () {
                var elegido = casilla.checked;

                // El FormData se arma ANTES de deshabilitar: un control
                // deshabilitado no viaja en el envío, y sin el campo "valor"
                // el servidor entendía siempre "desactivar" (el toggle podía
                // apagar pero nunca volver a prender).
                var datos = new FormData(form);
                casilla.disabled = true;

                fetch(form.action, {
                    method: 'POST',
                    body: datos,
                    headers: { 'X-Requested-With': 'fetch' },
                })
                    .then(function (r) { return r.json(); })
                    .then(function (respuesta) {
                        if (!respuesta.ok) throw new Error(respuesta.mensaje);
                        anterior = elegido;
                        marcarGuardado(form);
                    })
                    .catch(function (e) {
                        casilla.checked = anterior;
                        alert('No se pudo guardar el cambio. ' +
                              'Probá de nuevo o recargá la página.\n\n' + e.message);
                    })
                    .then(function () {
                        casilla.disabled = false;
                    });
            });
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        iniciarTipoDePrecio();
        iniciarCategoriaNueva();
        iniciarEstadoEnLinea();
        iniciarMarcasEnLinea();
    });
})();
