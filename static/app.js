/* =========================================================================
   SEMILLA TIENDA NATURAL — comportamiento común a todas las páginas
   Carrito (localStorage) · autocompletado · selector 100g/1kg ·
   navegación mobile · header sticky
   ========================================================================= */
(function () {
    'use strict';

    var CLAVE_CARRITO = 'carrito_semilla';
    var NUMERO_WHATSAPP = '5493515130094';

    /* --- utilidades --------------------------------------------------- */

    function esc(texto) {
        return String(texto).replace(/[&<>"']/g, function (c) {
            return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
        });
    }

    function pesos(n) {
        return Number(n).toLocaleString('es-AR');
    }

    /* --- stock ---------------------------------------------------------
       El catálogo puede cambiar después de que el cliente armó el carrito:
       esta lista, que viene renderizada en la página, permite detectar lo
       que se agotó mientras tanto. */

    var _sinStock = null;

    function nombresSinStock() {
        if (_sinStock !== null) return _sinStock;
        _sinStock = [];
        var el = document.getElementById('datos-sin-stock');
        if (el) {
            try {
                var lista = JSON.parse(el.textContent);
                if (Array.isArray(lista)) _sinStock = lista;
            } catch (e) {
                _sinStock = [];
            }
        }
        return _sinStock;
    }

    function estaAgotado(nombre) {
        return nombresSinStock().indexOf(nombre) !== -1;
    }

    function leerCarrito() {
        try {
            return JSON.parse(localStorage.getItem(CLAVE_CARRITO)) || [];
        } catch (e) {
            return [];
        }
    }

    function guardarCarrito(carrito) {
        localStorage.setItem(CLAVE_CARRITO, JSON.stringify(carrito));
    }

    /* --- carrito ------------------------------------------------------ */

    function abrirCarrito() {
        var panel = document.getElementById('carrito-lateral');
        if (!panel) return;
        panel.classList.add('abierto');
        document.getElementById('overlay').classList.add('abierto');
        actualizarInterfaz();
    }

    function cerrarCarrito() {
        var panel = document.getElementById('carrito-lateral');
        if (!panel) return;
        panel.classList.remove('abierto');
        sincronizarOverlay();
    }

    function toggleCarrito() {
        var panel = document.getElementById('carrito-lateral');
        if (!panel) return;
        if (panel.classList.contains('abierto')) {
            cerrarCarrito();
        } else {
            abrirCarrito();
        }
    }

    function agregarAlCarrito(nombre, precio, presentacion) {
        // Último cerrojo: un producto agotado no entra al carrito por
        // ningún camino, ni siquiera llamando a esta función a mano.
        if (estaAgotado(nombre)) {
            alert('«' + nombre + '» está sin stock por el momento.');
            return;
        }

        var carrito = leerCarrito();
        var clave = nombre + '|' + presentacion;
        var index = carrito.findIndex(function (p) { return p.clave === clave; });

        if (index !== -1) {
            carrito[index].cantidad++;
        } else {
            carrito.push({
                clave: clave,
                nombre: nombre,
                precio: precio,
                presentacion: presentacion,
                cantidad: 1
            });
        }

        guardarCarrito(carrito);
        abrirCarrito();
    }

    function cambiarCantidad(index, cambio) {
        var carrito = leerCarrito();
        if (!carrito[index]) return;

        carrito[index].cantidad += cambio;
        if (carrito[index].cantidad <= 0) {
            carrito.splice(index, 1);
        }

        guardarCarrito(carrito);
        actualizarInterfaz();
    }

    function actualizarInterfaz() {
        var carrito = leerCarrito();
        var contenedor = document.getElementById('carrito-items');
        var totalTxt = document.getElementById('carrito-total');
        var badge = document.getElementById('cart-count');

        var total = 0;
        var unidades = 0;

        carrito.forEach(function (item) {
            // Lo que se agotó después de agregarlo no suma al total
            if (!estaAgotado(item.nombre)) {
                total += item.precio * item.cantidad;
            }
            unidades += item.cantidad;
        });

        if (totalTxt) totalTxt.innerText = pesos(total);
        if (badge) badge.innerText = unidades;
        if (!contenedor) return;

        if (carrito.length === 0) {
            contenedor.innerHTML = '<p class="carrito-vacio">Tu carrito está vacío.</p>';
            return;
        }

        contenedor.innerHTML = carrito.map(function (item, index) {
            var agotado = estaAgotado(item.nombre);
            var subtotal = item.precio * item.cantidad;
            var detalle = agotado
                ? 'Sin stock por el momento'
                : (item.presentacion !== 'unidad' ? esc(item.presentacion) + ' — ' : '') +
                  (item.precio > 0 ? '$' + pesos(item.precio) + ' c/u' : 'A confirmar');
            var lineaSubtotal = (!agotado && item.cantidad > 1 && item.precio > 0)
                ? '<p class="item-subtotal">Subtotal: $' + pesos(subtotal) + '</p>'
                : '';
            var etiqueta = agotado
                ? '<span class="item-sin-stock">Sin stock</span>'
                : '';

            return '' +
                '<div class="item-carrito' + (agotado ? ' agotado' : '') + '">' +
                    '<div class="item-info">' +
                        '<p class="item-nombre">' + esc(item.nombre) + etiqueta + '</p>' +
                        '<p class="item-detalle">' + detalle + '</p>' +
                        lineaSubtotal +
                    '</div>' +
                    '<div class="stepper-container-mini">' +
                        '<button type="button" class="btn-stepper" data-accion="cantidad" ' +
                            'data-index="' + index + '" data-delta="-1" aria-label="Quitar una unidad">' +
                            '<svg class="ico ico-chico" aria-hidden="true"><use href="#ico-menos"></use></svg>' +
                        '</button>' +
                        '<span class="stepper-cantidad">' + item.cantidad + '</span>' +
                        '<button type="button" class="btn-stepper" data-accion="cantidad" ' +
                            'data-index="' + index + '" data-delta="1" aria-label="Agregar una unidad">' +
                            '<svg class="ico ico-chico" aria-hidden="true"><use href="#ico-mas"></use></svg>' +
                        '</button>' +
                    '</div>' +
                '</div>';
        }).join('');
    }

    function enviarWhatsApp() {
        var carrito = leerCarrito();

        if (carrito.length === 0) {
            alert('Tu carrito está vacío.');
            return;
        }

        // Lo agotado no viaja en el pedido
        var pedibles = carrito.filter(function (item) {
            return !estaAgotado(item.nombre);
        });

        if (pedibles.length === 0) {
            alert('Los productos de tu carrito están sin stock por el momento.');
            return;
        }

        var mensaje = '*Hola! Quiero hacer un pedido en Semilla Tienda Natural:*\n\n';
        var total = 0;

        pedibles.forEach(function (item) {
            var subtotal = item.precio * item.cantidad;
            total += subtotal;
            var etiqueta = item.presentacion !== 'unidad' ? ' (' + item.presentacion + ')' : '';

            if (item.precio > 0) {
                mensaje += '• ' + item.nombre + etiqueta + ' x' + item.cantidad +
                    ' = $' + pesos(subtotal) + '\n';
            } else {
                mensaje += '• ' + item.nombre + etiqueta + ' x' + item.cantidad +
                    ' (consultar precio)\n';
            }
        });

        if (total > 0) {
            mensaje += '\n*Total estimado: $' + pesos(total) + '*';
        }
        mensaje += '\n\n¡Gracias!';

        window.open('https://wa.me/' + NUMERO_WHATSAPP + '?text=' + encodeURIComponent(mensaje), '_blank');
    }

    /* --- selector 100g / 1kg ------------------------------------------ */

    function seleccionarPresentacion(boton) {
        var card = boton.closest('.producto-card');
        if (!card) return;

        var presentacion = boton.dataset.presentacion;
        var precio = Number(presentacion === '1kg' ? card.dataset.precioKg : card.dataset.precio100g) || 0;
        var unidad = presentacion === '1kg' ? '/ 1kg' : '/ 100g';

        card.querySelectorAll('.seg-btn').forEach(function (b) {
            b.classList.remove('activo');
            b.setAttribute('aria-pressed', 'false');
        });
        boton.classList.add('activo');
        boton.setAttribute('aria-pressed', 'true');
        card.dataset.presentacionActiva = presentacion;

        var precioEl = card.querySelector('.precio');
        if (precioEl) {
            precioEl.innerHTML = precio > 0
                ? '<span class="precio-monto">$' + pesos(precio) + '</span>' +
                  '<span class="precio-unidad">' + unidad + '</span>'
                : '<span class="precio-consultar">Precio a confirmar</span>';
        }

        // El ocre solo aparece si 1 kg está activo y hay un precio que comparar
        var nota = card.querySelector('.nota-ahorro');
        if (nota) {
            nota.hidden = !(presentacion === '1kg' && Number(card.dataset.precioKg) > 0);
        }
    }

    /* --- navegación mobile, buscador y overlay ------------------------ */

    function abrirMenu() {
        document.getElementById('nav-mobile').classList.add('abierto');
        document.getElementById('overlay').classList.add('abierto');
        document.body.classList.add('sin-scroll');
        var btn = document.querySelector('[data-accion="abrir-menu"]');
        if (btn) btn.setAttribute('aria-expanded', 'true');
    }

    function cerrarMenu() {
        document.getElementById('nav-mobile').classList.remove('abierto');
        document.body.classList.remove('sin-scroll');
        var btn = document.querySelector('[data-accion="abrir-menu"]');
        if (btn) btn.setAttribute('aria-expanded', 'false');
        sincronizarOverlay();
    }

    // El overlay es compartido: solo se apaga si no queda ningún panel abierto
    function sincronizarOverlay() {
        var menu = document.getElementById('nav-mobile');
        var carrito = document.getElementById('carrito-lateral');
        var hayPanel = (menu && menu.classList.contains('abierto')) ||
                       (carrito && carrito.classList.contains('abierto'));
        document.getElementById('overlay').classList.toggle('abierto', hayPanel);
    }

    function toggleBuscador() {
        var header = document.getElementById('sitio-header');
        header.classList.toggle('buscador-abierto');
        if (header.classList.contains('buscador-abierto')) {
            var input = document.getElementById('search-input');
            if (input) input.focus();
        }
    }

    function toggleAcordeon(boton) {
        var abierto = boton.getAttribute('aria-expanded') === 'true';
        boton.setAttribute('aria-expanded', abierto ? 'false' : 'true');
        var panel = boton.nextElementSibling;
        if (panel) panel.classList.toggle('abierto', !abierto);
    }

    /* --- autocompletado (misma lógica y mismo endpoint) --------------- */

    function iniciarAutocompletado() {
        var input = document.getElementById('search-input');
        var lista = document.getElementById('autocomplete-lista');
        if (!input || !lista) return;

        var timeoutId;

        input.addEventListener('input', function () {
            clearTimeout(timeoutId);
            var q = input.value.trim();

            if (q.length < 1) {
                lista.hidden = true;
                return;
            }

            timeoutId = setTimeout(function () {
                fetch('/buscar?q=' + encodeURIComponent(q))
                    .then(function (r) { return r.json(); })
                    .then(function (resultados) {
                        if (resultados.length === 0) {
                            lista.innerHTML = '<div class="autocomplete-vacio">Sin resultados</div>';
                        } else {
                            lista.innerHTML = resultados.map(function (p) {
                                // Los agotados se siguen mostrando, pero apagados
                                var agotado = p.stock === 'sin_stock';
                                return '<div class="autocomplete-item' + (agotado ? ' agotado' : '') +
                                    '" data-nombre="' + esc(p.nombre) + '">' +
                                    '<span class="autocomplete-nombre">' + esc(p.nombre) +
                                        (agotado ? ' <span class="autocomplete-agotado">sin stock</span>' : '') +
                                    '</span>' +
                                    '<span class="autocomplete-categoria">' + esc(p.categoria) + '</span>' +
                                    '</div>';
                            }).join('');
                        }
                        lista.hidden = false;
                    });
            }, 200);
        });

        lista.addEventListener('click', function (e) {
            var item = e.target.closest('.autocomplete-item');
            if (!item) return;
            window.location.href = '/compras?q=' + encodeURIComponent(item.dataset.nombre);
        });

        document.addEventListener('click', function (e) {
            if (!input.contains(e.target) && !lista.contains(e.target)) {
                lista.hidden = true;
            }
        });
    }

    /* --- header sticky ------------------------------------------------ */

    function iniciarHeaderSticky() {
        var header = document.getElementById('sitio-header');
        if (!header) return;

        var actualizar = function () {
            header.classList.toggle('desprendido', window.scrollY > 8);
        };

        actualizar();
        window.addEventListener('scroll', actualizar, { passive: true });
    }

    /* --- delegación de eventos ---------------------------------------- */

    document.addEventListener('click', function (e) {
        var disparador = e.target.closest('[data-accion]');
        if (!disparador) return;

        switch (disparador.dataset.accion) {
            case 'toggle-carrito':
                toggleCarrito();
                break;
            case 'agregar':
                var card = disparador.closest('.producto-card');
                if (!card) break;
                var presentacion = card.dataset.presentacionActiva || 'unidad';
                var precio = presentacion === '1kg' ? card.dataset.precioKg
                    : presentacion === '100g' ? card.dataset.precio100g
                    : card.dataset.precio;
                agregarAlCarrito(card.dataset.nombre, Number(precio) || 0, presentacion);
                break;
            case 'presentacion':
                seleccionarPresentacion(disparador);
                break;
            case 'cantidad':
                cambiarCantidad(Number(disparador.dataset.index), Number(disparador.dataset.delta));
                break;
            case 'avisar':
                var cardAgotada = disparador.closest('.producto-card');
                if (!cardAgotada) break;
                var consulta = 'Hola! Quería consultar cuándo vuelve a estar disponible: ' +
                    cardAgotada.dataset.nombre;
                window.open('https://wa.me/' + NUMERO_WHATSAPP + '?text=' +
                    encodeURIComponent(consulta), '_blank');
                break;
            case 'checkout':
                enviarWhatsApp();
                break;
            case 'abrir-menu':
                abrirMenu();
                break;
            case 'cerrar-menu':
                cerrarMenu();
                break;
            case 'cerrar-todo':
                cerrarMenu();
                cerrarCarrito();
                break;
            case 'toggle-buscador':
                toggleBuscador();
                break;
            case 'acordeon':
                toggleAcordeon(disparador);
                break;
        }
    });

    document.addEventListener('keydown', function (e) {
        if (e.key !== 'Escape') return;
        cerrarMenu();
        cerrarCarrito();
        var lista = document.getElementById('autocomplete-lista');
        if (lista) lista.hidden = true;
    });

    document.addEventListener('DOMContentLoaded', function () {
        actualizarInterfaz();   // el contador debe reflejar el localStorage ya en la carga
        iniciarAutocompletado();
        iniciarHeaderSticky();
    });

    // API pública mínima, por si hace falta llamarla desde el HTML
    window.toggleCarrito = toggleCarrito;
    window.agregarAlCarrito = agregarAlCarrito;
    window.enviarWhatsApp = enviarWhatsApp;
})();
