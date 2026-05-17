from flask import Flask, render_template, request

app = Flask(__name__)

# --- BASE DE PRODUCTOS ---
# Todos los productos con nombre, precio, categoria y descripcion
productos = [
    # MIX DE FRUTOS SECOS
    # precio_100g = precio por 100 gramos
    # precio_kg   = precio por 1 kilogramo (más barato que 10x el de 100g)
    # Si el producto NO se vende a granel, usar solo "precio" y omitir precio_100g/precio_kg
    {
        "id": 1,
        "nombre": "Mix Energy",
        "descripcion": "Nuez, almendra, castañas de cajú, maní, pasas de uva negras y rubias.",
        "precio_100g": 2000,
        "precio_kg": 18000,
        "categoria": "Mix de Frutos Secos",
        "imagen": "mix_energy.jpg"
    },
    {
        "id": 2,
        "nombre": "Mix Energy sin Maní",
        "descripcion": "Nuez, almendra, castañas de cajú, pasas de uva negras y rubias.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Mix de Frutos Secos",
        "imagen": "mix_energy_sin_mani.jpg"
    },
    {
        "id": 3,
        "nombre": "Mix Tropical",
        "descripcion": "Nuez, almendra, castañas de cajú, maní, pasas de uva, bananas glaseadas, ananá glaseado.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Mix de Frutos Secos",
        "imagen": "mix_tropical.jpg"
    },
    {
        "id": 4,
        "nombre": "Mix Frutos Secos",
        "descripcion": "Nuez, almendra, castañas de cajú, maní, avellanas.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Mix de Frutos Secos",
        "imagen": "mix_frutos_secos.jpg"
    },
    {
        "id": 5,
        "nombre": "Mix Frutos Secos sin Maní",
        "descripcion": "Nuez, almendra, castañas de cajú, avellanas.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Mix de Frutos Secos",
        "imagen": "mix_frutos_sin_mani.jpg"
    },
    {
        "id": 6,
        "nombre": "Mix Salty",
        "descripcion": "Castañas saladas, maní salado, semillas de girasol, semillas de zapallo, maíz frito.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Mix de Frutos Secos",
        "imagen": "mix_salty.jpg"
    },
    {
        "id": 7,
        "nombre": "Mix Ahumado",
        "descripcion": "Castañas, almendras y maní salados.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Mix de Frutos Secos",
        "imagen": "mix_ahumado.jpg"
    },

    # CASTAÑAS DE CAJÚ
    

    # ALMENDRAS
   

    # NUECES
    

    # FRUTAS DESHIDRATADAS
    

    # GRANOLAS
    {
        "id": 8,
        "nombre": "Granola Omega Monarca",
        "descripcion": "Granola enriquecida con semillas omega. Marca Monarca.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Granolas",
        "imagen": "granola_omega_monarca.jpg"
    },
    {
        "id": 9,
        "nombre": "Granola Peanut Butter Monarca",
        "descripcion": "Granola con mantequilla de maní. Marca Monarca.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Granolas",
        "imagen": "granola_peanut_butter_monarca.jpg"
    },
    {
        "id": 10,
        "nombre": "Granola Premium Monarca",
        "descripcion": "Granola premium con ingredientes seleccionados. Marca Monarca.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Granolas",
        "imagen": "granola_premium_monarca.jpg"
    },
    {
        "id": 11,
        "nombre": "Granola Stevia Monarca",
        "descripcion": "Granola endulzada con stevia, sin azúcar añadida. Marca Monarca.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Granolas",
        "imagen": "granola_stevia_monarca.jpg"
    },
    {
        "id": 12,
        "nombre": "Granola Ultra Protein Monarca",
        "descripcion": "Granola alta en proteínas. Ideal para deportistas. Marca Monarca.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Granolas",
        "imagen": "granola_ultra_protein_monarca.jpg"
    },
    {
        "id": 13,
        "nombre": "Granola Keto Monarca",
        "descripcion": "Granola apta para dieta cetogénica, baja en carbohidratos. Marca Monarca.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Granolas",
        "imagen": "granola_keto_monarca.jpg"
    },
    {
        "id": 14,
        "nombre": "Granola Tropical Monarca",
        "descripcion": "Granola con frutas tropicales deshidratadas. Marca Monarca.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Granolas",
        "imagen": "granola_tropical_monarca.jpg"
    },
    {
        "id": 15,
        "nombre": "Granola Almendra Cajú Arándanos Íntegra",
        "descripcion": "Granola con almendras, castañas de cajú y arándanos. Marca Íntegra.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Granolas",
        "imagen": "granola_almendra_caju_arandanos_integra.jpg"
    },
    {
        "id": 16,
        "nombre": "Granola Chocolate Cacao Almendra Íntegra",
        "descripcion": "Granola con chocolate, cacao y almendras. Marca Íntegra.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Granolas",
        "imagen": "granola_chocolate_cacao_almendra_integra.jpg"
    },

    # HARINAS — A GRANEL (precio por 100g y por kg)
    {
        "id": 17,
        "nombre": "Harina de Trigo Integral Premium Molcol",
        "descripcion": "Harina de trigo integral premium. Marca Molcol.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Harinas",
        "subcategoria": "Harina Trigo",
        "imagen": "harina_trigo_integral_molcol.jpg"
    },
    {
        "id": 18,
        "nombre": "Harina de Trigo Integral Orgánica Brotes",
        "descripcion": "Harina de trigo integral de cultivo orgánico certificado. Marca Brotes.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Harinas",
        "subcategoria": "Harina Trigo",
        "imagen": "harina_trigo_integral_organica_brotes.jpg"
    },
    {
        "id": 19,
        "nombre": "Harina de Trigo Sarraceno Olienka",
        "descripcion": "Harina de trigo sarraceno. Marca Olienka.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Harinas",
        "subcategoria": "Harina Trigo",
        "imagen": "harina_trigo_sarraceno_olienka.jpg"
    },
    {
        "id": 20,
        "nombre": "Harina de Almendras con Piel Nacional",
        "descripcion": "Harina de almendras con piel, de origen nacional.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Harinas",
        "subcategoria": "Harina Frutos Secos",
        "imagen": "harina_almendras_con_piel_nacional.jpg"
    },
    {
        "id": 21,
        "nombre": "Harina de Almendras sin Piel Nacional",
        "descripcion": "Harina de almendras sin piel, de origen nacional.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Harinas",
        "subcategoria": "Harina Frutos Secos",
        "imagen": "harina_almendras_sin_piel_nacional.jpg"
    },
    {
        "id": 22,
        "nombre": "Harina de Almendras sin Piel Premium",
        "descripcion": "Harina de almendras sin piel de calidad premium.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Harinas",
        "subcategoria": "Harina Frutos Secos",
        "imagen": "harina_almendras_sin_piel_premium.jpg"
    },
    {
        "id": 23,
        "nombre": "Harina de Castañas de Cajú",
        "descripcion": "Harina de castañas de cajú, suave y versátil.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Harinas",
        "subcategoria": "Harina Frutos Secos",
        "imagen": "harina_castanas_caju.jpg"
    },
    {
        "id": 24,
        "nombre": "Harina de Coco",
        "descripcion": "Harina de coco, alta en fibra y baja en carbohidratos.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Harinas",
        "subcategoria": "Harina Otras",
        "imagen": "harina_coco.jpg"
    },
    {
        "id": 25,
        "nombre": "Harina de Algarroba",
        "descripcion": "Harina de algarroba, naturalmente dulce. Ideal para repostería.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Harinas",
        "subcategoria": "Harina Otras",
        "imagen": "harina_algarroba.jpg"
    },
    {
        "id": 26,
        "nombre": "Harina de Garbanzo Molcol",
        "descripcion": "Harina de garbanzo, rica en proteínas. Marca Molcol.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Harinas",
        "subcategoria": "Harina Legumbres",
        "imagen": "harina_garbanzo_molcol.jpg"
    },
    {
        "id": 27,
        "nombre": "Harina de Soja Molcol",
        "descripcion": "Harina de soja, alto contenido proteico. Marca Molcol.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Harinas",
        "subcategoria": "Harina Legumbres",
        "imagen": "harina_soja_molcol.jpg"
    },
    {
        "id": 28,
        "nombre": "Harina de Lino Sol Azteca",
        "descripcion": "Harina de lino, rica en omega-3 y fibra. Marca Sol Azteca.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Harinas",
        "subcategoria": "Harina Semillas",
        "imagen": "harina_lino_sol_azteca.jpg"
    },
    {
        "id": 29,
        "nombre": "Harina de Chía Sol Azteca",
        "descripcion": "Harina de chía, rica en omega-3, proteínas y antioxidantes. Marca Sol Azteca.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Harinas",
        "subcategoria": "Harina Semillas",
        "imagen": "harina_chia_sol_azteca.jpg"
    },
    {
        "id": 30,
        "nombre": "Harina de Sésamo Integral Sol Azteca",
        "descripcion": "Harina de sésamo integral, rica en calcio y minerales. Marca Sol Azteca.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Harinas",
        "subcategoria": "Harina Semillas",
        "imagen": "harina_sesamo_integral_sol_azteca.jpg"
    },
    {
        "id": 31,
        "nombre": "Harina de Maíz Abatí Molcol",
        "descripcion": "Harina de maíz abatí, ideal para sopa paraguaya. Marca Molcol.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Harinas",
        "subcategoria": "Harina Cereales",
        "imagen": "harina_maiz_abati_molcol.jpg"
    },
    {
        "id": 32,
        "nombre": "Harina de Avena Molcol",
        "descripcion": "Harina de avena, ideal para repostería y panificados. Marca Molcol.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Harinas",
        "subcategoria": "Harina Cereales",
        "imagen": "harina_avena_molcol.jpg"
    },
    {
        "id": 33,
        "nombre": "Harina de Centeno Molcol",
        "descripcion": "Harina de centeno, ideal para panes oscuros. Marca Molcol.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Harinas",
        "subcategoria": "Harina Cereales",
        "imagen": "harina_centeno_molcol.jpg"
    },

    # HARINAS — ENVASE CERRADO (precio por unidad)
    {
        "id": 34,
        "nombre": "Harina de Maíz Amarillo Precocida Pan x 1 kg",
        "descripcion": "Harina de maíz amarillo precocida, ideal para arepas. Marca Pan. Por unidad de 1 kg.",
        "precio": 0,
        "categoria": "Harinas",
        "subcategoria": "Harina Cereales",
        "imagen": "harina_maiz_pan.jpg"
    },
    {
        "id": 35,
        "nombre": "Harina de Maní Desgrasada Snackwell x 250 g — SIN TACC",
        "descripcion": "Harina de maní desgrasada en envase cerrado. Apta celíacos. SIN TACC. Marca Snackwell. Por unidad de 250 g.",
        "precio": 0,
        "categoria": "Harinas",
        "subcategoria": "Harina Frutos Secos",
        "imagen": "harina_mani_snackwell.jpg"
    },
    {
        "id": 36,
        "nombre": "Harina de Quinoa Natural Seed x 250 g — SIN TACC",
        "descripcion": "Harina de quinoa en envase cerrado. Apta celíacos. SIN TACC. Marca Natural Seed. Por unidad de 250 g.",
        "precio": 0,
        "categoria": "Harinas",
        "subcategoria": "Harina Cereales",
        "imagen": "harina_quinoa_natural_seed.jpg"
    },
    {
        "id": 37,
        "nombre": "Harina de Girasol Natural Seed x 250 g — SIN TACC",
        "descripcion": "Harina de girasol en envase cerrado. Apta celíacos. SIN TACC. Marca Natural Seed. Por unidad de 250 g.",
        "precio": 0,
        "categoria": "Harinas",
        "subcategoria": "Harina Semillas",
        "imagen": "harina_girasol_natural_seed.jpg"
    },
    {
        "id": 38,
        "nombre": "Harina de Almendras con Piel Natural Seed x 250 g — SIN TACC",
        "descripcion": "Harina de almendras con piel en envase cerrado. Apta celíacos. SIN TACC. Marca Natural Seed. Por unidad de 250 g.",
        "precio": 0,
        "categoria": "Harinas",
        "subcategoria": "Harina Frutos Secos",
        "imagen": "harina_almendras_piel_natural_seed.jpg"
    },

    # SEMILLAS
    

    # SUPLEMENTOS
    

    # TÉS E INFUSIONES
    

    # CEREALES Y LEGUMBRES

    # — LEGUMBRES —
    {
        "id": 39,
        "nombre": "Lentejas Rojas",
        "descripcion": "Lentejas rojas a granel, de cocción rápida.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Cereales y Legumbres",
        "subcategoria": "Legumbres",
        "imagen": "lentejas_rojas.jpg"
    },
    {
        "id": 40,
        "nombre": "Lentejón",
        "descripcion": "Lentejón a granel, de mayor tamaño que la lenteja común.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Cereales y Legumbres",
        "subcategoria": "Legumbres",
        "imagen": "lentejon.jpg"
    },
    {
        "id": 41,
        "nombre": "Lentejas",
        "descripcion": "Lentejas clásicas a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Cereales y Legumbres",
        "subcategoria": "Legumbres",
        "imagen": "lentejas.jpg"
    },
    {
        "id": 42,
        "nombre": "Poroto Alubia",
        "descripcion": "Poroto alubia blanco a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Cereales y Legumbres",
        "subcategoria": "Legumbres",
        "imagen": "poroto_alubia.jpg"
    },
    {
        "id": 43,
        "nombre": "Poroto Negro",
        "descripcion": "Poroto negro a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Cereales y Legumbres",
        "subcategoria": "Legumbres",
        "imagen": "poroto_negro.jpg"
    },
    {
        "id": 44,
        "nombre": "Poroto Aduki",
        "descripcion": "Poroto aduki a granel, muy usado en cocina oriental y macrobiótica.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Cereales y Legumbres",
        "subcategoria": "Legumbres",
        "imagen": "poroto_aduki.jpg"
    },
    {
        "id": 45,
        "nombre": "Porotos Lupines",
        "descripcion": "Porotos lupines a granel, ricos en proteínas.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Cereales y Legumbres",
        "subcategoria": "Legumbres",
        "imagen": "porotos_lupines.jpg"
    },
    {
        "id": 46,
        "nombre": "Porotos Pallares",
        "descripcion": "Porotos pallares a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Cereales y Legumbres",
        "subcategoria": "Legumbres",
        "imagen": "porotos_pallares.jpg"
    },
    {
        "id": 47,
        "nombre": "Poroto Colorado",
        "descripcion": "Poroto colorado a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Cereales y Legumbres",
        "subcategoria": "Legumbres",
        "imagen": "poroto_colorado.jpg"
    },
    {
        "id": 48,
        "nombre": "Poroto Bolita",
        "descripcion": "Poroto bolita a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Cereales y Legumbres",
        "subcategoria": "Legumbres",
        "imagen": "poroto_bolita.jpg"
    },
    {
        "id": 49,
        "nombre": "Poroto de Soja",
        "descripcion": "Poroto de soja a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Cereales y Legumbres",
        "subcategoria": "Legumbres",
        "imagen": "poroto_soja.jpg"
    },
    {
        "id": 50,
        "nombre": "Garbanzos",
        "descripcion": "Garbanzos a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Cereales y Legumbres",
        "subcategoria": "Legumbres",
        "imagen": "garbanzos.jpg"
    },
    {
        "id": 51,
        "nombre": "Arvejas",
        "descripcion": "Arvejas a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Cereales y Legumbres",
        "subcategoria": "Legumbres",
        "imagen": "arvejas.jpg"
    },
    {
        "id": 52,
        "nombre": "Soja Texturizada Fina",
        "descripcion": "Soja texturizada fina a granel, ideal para guisos y preparaciones.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Cereales y Legumbres",
        "subcategoria": "Legumbres",
        "imagen": "soja_texturizada_fina.jpg"
    },
    {
        "id": 53,
        "nombre": "Soja Texturizada Gruesa",
        "descripcion": "Soja texturizada gruesa a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Cereales y Legumbres",
        "subcategoria": "Legumbres",
        "imagen": "soja_texturizada_gruesa.jpg"
    },

    # — CEREALES —
    {
        "id": 54,
        "nombre": "Trigo Candeal Pelado",
        "descripcion": "Trigo candeal pelado a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Cereales y Legumbres",
        "subcategoria": "Cereales",
        "imagen": "trigo_candeal_pelado.jpg"
    },
    {
        "id": 55,
        "nombre": "Trigo Burgol Fino",
        "descripcion": "Trigo burgol fino a granel, ideal para taboulé y ensaladas.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Cereales y Legumbres",
        "subcategoria": "Cereales",
        "imagen": "trigo_burgol_fino.jpg"
    },
    {
        "id": 56,
        "nombre": "Maíz Pisingallo",
        "descripcion": "Maíz pisingallo a granel, ideal para pochoclo.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Cereales y Legumbres",
        "subcategoria": "Cereales",
        "imagen": "maiz_pisingallo.jpg"
    },
    {
        "id": 57,
        "nombre": "Maíz Blanco",
        "descripcion": "Maíz blanco a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Cereales y Legumbres",
        "subcategoria": "Cereales",
        "imagen": "maiz_blanco.jpg"
    },

    # — MANÍ —
    {
        "id": 58,
        "nombre": "Maní Crudo",
        "descripcion": "Maní crudo a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Cereales y Legumbres",
        "subcategoria": "Maní",
        "imagen": "mani_crudo.jpg"
    },
    {
        "id": 59,
        "nombre": "Maní Sin Sal",
        "descripcion": "Maní tostado sin sal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Cereales y Legumbres",
        "subcategoria": "Maní",
        "imagen": "mani_sin_sal.jpg"
    },
    {
        "id": 60,
        "nombre": "Maní Con Sal",
        "descripcion": "Maní tostado con sal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Cereales y Legumbres",
        "subcategoria": "Maní",
        "imagen": "mani_con_sal.jpg"
    },
    {
        "id": 61,
        "nombre": "Maní Con Cáscara",
        "descripcion": "Maní con cáscara a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Cereales y Legumbres",
        "subcategoria": "Maní",
        "imagen": "mani_con_cascara.jpg"
    },

    # ARROCES
    {
        "id": 62,
        "nombre": "Arroz Yamani",
        "descripcion": "Arroz yamani integral a granel, rico en fibra y nutrientes.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Arroces",
        "imagen": "arroz_yamani.jpg"
    },
    {
        "id": 63,
        "nombre": "Arroz Integral Largo Fino",
        "descripcion": "Arroz integral largo fino a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Arroces",
        "imagen": "arroz_integral_largo_fino.jpg"
    },
    {
        "id": 64,
        "nombre": "Arroz Koshihikari",
        "descripcion": "Arroz japonés koshihikari a granel, de grano corto y textura cremosa.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Arroces",
        "imagen": "arroz_koshihikari.jpg"
    },

    # CHOCOLATERÍA
    {
        "id": 164,
        "nombre": "Almendras Bañadas en Chocolate Negro",
        "descripcion": "Almendras bañadas en chocolate negro a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Chocolatería",
        "imagen": "almendras_chocolate_negro.jpg"
    },
    {
        "id": 165,
        "nombre": "Almendras Bañadas en Chocolate Blanco",
        "descripcion": "Almendras bañadas en chocolate blanco a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Chocolatería",
        "imagen": "almendras_chocolate_blanco.jpg"
    },
    {
        "id": 166,
        "nombre": "Pasas de Uva Bañadas en Chocolate Negro",
        "descripcion": "Pasas de uva bañadas en chocolate negro a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Chocolatería",
        "imagen": "pasas_chocolate_negro.jpg"
    },
    {
        "id": 167,
        "nombre": "Maní Bañado en Chocolate Negro Semiamargo",
        "descripcion": "Maní bañado en chocolate negro semiamargo a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Chocolatería",
        "imagen": "mani_chocolate_semiamargo.jpg"
    },
    {
        "id": 168,
        "nombre": "Lentejas de Chocolate",
        "descripcion": "Lentejas de chocolate a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Chocolatería",
        "imagen": "lentejas_chocolate.jpg"
    },
    {
        "id": 169,
        "nombre": "Mini Rocklets",
        "descripcion": "Mini rocklets a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Chocolatería",
        "imagen": "mini_rocklets.jpg"
    },
    {
        "id": 170,
        "nombre": "Gotas de Chocolate Blanco",
        "descripcion": "Gotas de chocolate blanco a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Chocolatería",
        "imagen": "gotas_chocolate_blanco.jpg"
    },
    {
        "id": 171,
        "nombre": "Gotas de Chocolate Negro",
        "descripcion": "Gotas de chocolate negro a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Chocolatería",
        "imagen": "gotas_chocolate_negro.jpg"
    },

    # TÉS E INFUSIONES
    {
        "id": 161,
        "nombre": "Té Negro en Hebras",
        "descripcion": "Té negro en hebras a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Tés e Infusiones",
        "imagen": "te_negro.jpg"
    },
    {
        "id": 162,
        "nombre": "Té Verde en Hebras",
        "descripcion": "Té verde en hebras a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Tés e Infusiones",
        "imagen": "te_verde.jpg"
    },
    {
        "id": 163,
        "nombre": "Té Rojo en Hebras",
        "descripcion": "Té rojo en hebras a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Tés e Infusiones",
        "imagen": "te_rojo.jpg"
    },

    # ACEITES
    {
        "id": 172,
        "nombre": "Aceite de Oliva Virgen Extra Chaquiago x 500 ml",
        "descripcion": "Aceite de oliva virgen extra. Marca Chaquiago. Por unidad de 500 ml.",
        "precio": 0,
        "categoria": "Aceites",
        "imagen": "aceite_oliva_chaquiago_500.jpg"
    },
    {
        "id": 173,
        "nombre": "Aceite de Oliva Virgen Extra Chaquiago x 5 lt",
        "descripcion": "Aceite de oliva virgen extra. Marca Chaquiago. Por unidad de 5 litros.",
        "precio": 0,
        "categoria": "Aceites",
        "imagen": "aceite_oliva_chaquiago_5lt.jpg"
    },
    {
        "id": 174,
        "nombre": "Aceite de Coco Virgen God Bless You x 125 ml",
        "descripcion": "Aceite de coco virgen. Marca God Bless You. Por unidad de 125 ml.",
        "precio": 0,
        "categoria": "Aceites",
        "imagen": "aceite_coco_virgen_gby_125.jpg"
    },
    {
        "id": 175,
        "nombre": "Aceite de Coco Virgen God Bless You x 225 ml",
        "descripcion": "Aceite de coco virgen. Marca God Bless You. Por unidad de 225 ml.",
        "precio": 0,
        "categoria": "Aceites",
        "imagen": "aceite_coco_virgen_gby_225.jpg"
    },
    {
        "id": 176,
        "nombre": "Aceite de Coco Virgen God Bless You x 500 ml",
        "descripcion": "Aceite de coco virgen. Marca God Bless You. Por unidad de 500 ml.",
        "precio": 0,
        "categoria": "Aceites",
        "imagen": "aceite_coco_virgen_gby_500.jpg"
    },
    {
        "id": 177,
        "nombre": "Aceite de Coco Virgen x 1 lt",
        "descripcion": "Aceite de coco virgen a granel. Por unidad de 1 litro.",
        "precio": 0,
        "categoria": "Aceites",
        "imagen": "aceite_coco_virgen_1lt.jpg"
    },
    {
        "id": 178,
        "nombre": "Aceite de Coco Neutro God Bless You x 125 ml",
        "descripcion": "Aceite de coco neutro. Marca God Bless You. Por unidad de 125 ml.",
        "precio": 0,
        "categoria": "Aceites",
        "imagen": "aceite_coco_neutro_gby_125.jpg"
    },
    {
        "id": 179,
        "nombre": "Aceite de Coco Neutro God Bless You x 225 ml",
        "descripcion": "Aceite de coco neutro. Marca God Bless You. Por unidad de 225 ml.",
        "precio": 0,
        "categoria": "Aceites",
        "imagen": "aceite_coco_neutro_gby_225.jpg"
    },
    {
        "id": 180,
        "nombre": "Aceite de Coco Neutro God Bless You x 500 ml",
        "descripcion": "Aceite de coco neutro. Marca God Bless You. Por unidad de 500 ml.",
        "precio": 0,
        "categoria": "Aceites",
        "imagen": "aceite_coco_neutro_gby_500.jpg"
    },
    {
        "id": 181,
        "nombre": "Aceite de Coco Neutro x 1 lt",
        "descripcion": "Aceite de coco neutro. Por unidad de 1 litro.",
        "precio": 0,
        "categoria": "Aceites",
        "imagen": "aceite_coco_neutro_1lt.jpg"
    },
    {
        "id": 182,
        "nombre": "Aceite de Palta Chia Graal x 250 ml",
        "descripcion": "Aceite de palta. Marca Chia Graal. Por unidad de 250 ml.",
        "precio": 0,
        "categoria": "Aceites",
        "imagen": "aceite_palta_chia_graal_250.jpg"
    },
    {
        "id": 183,
        "nombre": "Aceite de Chía Sol Azteca x 150 ml",
        "descripcion": "Aceite de chía. Marca Sol Azteca. Por unidad de 150 ml.",
        "precio": 0,
        "categoria": "Aceites",
        "imagen": "aceite_chia_sol_azteca_150.jpg"
    },
    {
        "id": 184,
        "nombre": "Aceite de Sésamo Sol Azteca x 150 ml",
        "descripcion": "Aceite de sésamo. Marca Sol Azteca. Por unidad de 150 ml.",
        "precio": 0,
        "categoria": "Aceites",
        "imagen": "aceite_sesamo_sol_azteca_150.jpg"
    },
    {
        "id": 185,
        "nombre": "Aceite de Lino Sol Azteca x 150 ml",
        "descripcion": "Aceite de lino. Marca Sol Azteca. Por unidad de 150 ml.",
        "precio": 0,
        "categoria": "Aceites",
        "imagen": "aceite_lino_sol_azteca_150.jpg"
    },
    {
        "id": 186,
        "nombre": "Aceite de Almendras Sol Azteca x 100 ml",
        "descripcion": "Aceite de almendras. Marca Sol Azteca. Por unidad de 100 ml.",
        "precio": 0,
        "categoria": "Aceites",
        "imagen": "aceite_almendras_sol_azteca_100.jpg"
    },

    # VINAGRES
    {
        "id": 200,
        "nombre": "Vinagre de Vino Chaquiago x 1 lt",
        "descripcion": "Vinagre de vino. Marca Chaquiago. Por unidad de 1 litro.",
        "precio": 0,
        "categoria": "Vinagres",
        "imagen": "vinagre_vino_chaquiago_1lt.jpg"
    },
    {
        "id": 201,
        "nombre": "Vinagre de Alcohol Chaquiago x 1 lt",
        "descripcion": "Vinagre de alcohol. Marca Chaquiago. Por unidad de 1 litro.",
        "precio": 0,
        "categoria": "Vinagres",
        "imagen": "vinagre_alcohol_chaquiago_1lt.jpg"
    },
    {
        "id": 202,
        "nombre": "Vinagre de Manzana Orgánico Pampagourmet x 250 ml",
        "descripcion": "Vinagre de manzana orgánico. Marca Pampagourmet. Por unidad de 250 ml.",
        "precio": 0,
        "categoria": "Vinagres",
        "imagen": "vinagre_manzana_pampagourmet_250.jpg"
    },
    {
        "id": 203,
        "nombre": "Vinagre de Manzana Orgánico Pampagourmet x 500 ml",
        "descripcion": "Vinagre de manzana orgánico. Marca Pampagourmet. Por unidad de 500 ml.",
        "precio": 0,
        "categoria": "Vinagres",
        "imagen": "vinagre_manzana_pampagourmet_500.jpg"
    },

    # PASTAS UNTABLES
    {
        "id": 204,
        "nombre": "Pasta de Maní King Natural x 245 gr",
        "descripcion": "Pasta de maní natural. Marca King. Por unidad de 245 gr.",
        "precio": 0,
        "categoria": "Pastas Untables",
        "imagen": "mani_king_natural_245.jpg"
    },
    {
        "id": 205,
        "nombre": "Pasta de Maní King Natural x 485 gr",
        "descripcion": "Pasta de maní natural. Marca King. Por unidad de 485 gr.",
        "precio": 0,
        "categoria": "Pastas Untables",
        "imagen": "mani_king_natural_485.jpg"
    },
    {
        "id": 206,
        "nombre": "Pasta de Maní King Crunchy x 350 gr",
        "descripcion": "Pasta de maní crunchy. Marca King. Por unidad de 350 gr.",
        "precio": 0,
        "categoria": "Pastas Untables",
        "imagen": "mani_king_crunchy_350.jpg"
    },
    {
        "id": 207,
        "nombre": "Pasta de Maní King Vita+ x 350 gr",
        "descripcion": "Pasta de maní enriquecida con vitaminas. Marca King. Por unidad de 350 gr.",
        "precio": 0,
        "categoria": "Pastas Untables",
        "imagen": "mani_king_vita_350.jpg"
    },
    {
        "id": 208,
        "nombre": "Pasta de Maní Entrenuts Natural x 370 gr",
        "descripcion": "Pasta de maní natural. Marca Entrenuts. Por unidad de 370 gr.",
        "precio": 0,
        "categoria": "Pastas Untables",
        "imagen": "mani_entrenuts_natural_370.jpg"
    },
    {
        "id": 209,
        "nombre": "Pasta de Maní Entrenuts Coco x 370 gr",
        "descripcion": "Pasta de maní con coco. Marca Entrenuts. Por unidad de 370 gr.",
        "precio": 0,
        "categoria": "Pastas Untables",
        "imagen": "mani_entrenuts_coco_370.jpg"
    },
    {
        "id": 210,
        "nombre": "Pasta de Maní Entrenuts Sal Marina x 370 gr",
        "descripcion": "Pasta de maní con sal marina. Marca Entrenuts. Por unidad de 370 gr.",
        "precio": 0,
        "categoria": "Pastas Untables",
        "imagen": "mani_entrenuts_sal_370.jpg"
    },
    {
        "id": 211,
        "nombre": "Pasta de Maní Entrenuts Protein Salted Caramel x 370 gr",
        "descripcion": "Pasta de maní proteica sabor salted caramel. Marca Entrenuts. Por unidad de 370 gr.",
        "precio": 0,
        "categoria": "Pastas Untables",
        "imagen": "mani_entrenuts_salted_caramel_370.jpg"
    },
    {
        "id": 212,
        "nombre": "Pasta de Maní Entrenuts Protein Cookies and Cream x 370 gr",
        "descripcion": "Pasta de maní proteica sabor cookies and cream. Marca Entrenuts. Por unidad de 370 gr.",
        "precio": 0,
        "categoria": "Pastas Untables",
        "imagen": "mani_entrenuts_cookies_cream_370.jpg"
    },
    {
        "id": 213,
        "nombre": "Tahina de Sésamo Zeeny x 250 gr",
        "descripcion": "Pasta de sésamo (tahina). Marca Zeeny. Por unidad de 250 gr.",
        "precio": 0,
        "categoria": "Pastas Untables",
        "imagen": "tahina_zeeny_250.jpg"
    },
    {
        "id": 214,
        "nombre": "Pasta de Pistacho Felices las Vacas Endulzada x 220 gr",
        "descripcion": "Pasta de pistacho endulzada. Marca Felices las Vacas. Por unidad de 220 gr.",
        "precio": 0,
        "categoria": "Pastas Untables",
        "imagen": "pistacho_felices_vacas_220.jpg"
    },
    {
        "id": 215,
        "nombre": "Pasta de Pistacho Ancestral Natural x 200 gr",
        "descripcion": "Pasta de pistacho natural. Marca Ancestral. Por unidad de 200 gr.",
        "precio": 0,
        "categoria": "Pastas Untables",
        "imagen": "pistacho_ancestral_200.jpg"
    },
    {
        "id": 216,
        "nombre": "Pasta de Pistacho Sol Azteca Natural x 200 gr",
        "descripcion": "Pasta de pistacho natural. Marca Sol Azteca. Por unidad de 200 gr.",
        "precio": 0,
        "categoria": "Pastas Untables",
        "imagen": "pistacho_sol_azteca_200.jpg"
    },
    {
        "id": 217,
        "nombre": "Pasta de Calabaza Sol Azteca Natural x 200 gr",
        "descripcion": "Pasta de calabaza natural. Marca Sol Azteca. Por unidad de 200 gr.",
        "precio": 0,
        "categoria": "Pastas Untables",
        "imagen": "calabaza_sol_azteca_200.jpg"
    },
    {
        "id": 218,
        "nombre": "Pasta de Castañas de Cajú Sol Azteca Natural x 200 gr",
        "descripcion": "Pasta de castañas de cajú natural. Marca Sol Azteca. Por unidad de 200 gr.",
        "precio": 0,
        "categoria": "Pastas Untables",
        "imagen": "caju_sol_azteca_200.jpg"
    },
    {
        "id": 219,
        "nombre": "Pasta de Almendras Sol Azteca Natural x 200 gr",
        "descripcion": "Pasta de almendras natural. Marca Sol Azteca. Por unidad de 200 gr.",
        "precio": 0,
        "categoria": "Pastas Untables",
        "imagen": "almendras_sol_azteca_200.jpg"
    },
    {
        "id": 187,
        "nombre": "Jalapeño Verde Recetas de Entonces x 180 ml",
        "descripcion": "Salsa de jalapeño verde. Marca Recetas de Entonces. Por unidad de 180 ml.",
        "precio": 0,
        "categoria": "Salsas",
        "imagen": "jalapeno_verde_recetas_180.jpg"
    },
    {
        "id": 188,
        "nombre": "Jalapeño Ahumado Recetas de Entonces x 180 ml",
        "descripcion": "Salsa de jalapeño ahumado. Marca Recetas de Entonces. Por unidad de 180 ml.",
        "precio": 0,
        "categoria": "Salsas",
        "imagen": "jalapeno_ahumado_recetas_180.jpg"
    },
    {
        "id": 189,
        "nombre": "Jalapeño Rojo Recetas de Entonces x 180 ml",
        "descripcion": "Salsa de jalapeño rojo. Marca Recetas de Entonces. Por unidad de 180 ml.",
        "precio": 0,
        "categoria": "Salsas",
        "imagen": "jalapeno_rojo_recetas_180.jpg"
    },
    {
        "id": 190,
        "nombre": "Salsa de Soja Recetas de Entonces x 180 ml",
        "descripcion": "Salsa de soja. Marca Recetas de Entonces. Por unidad de 180 ml.",
        "precio": 0,
        "categoria": "Salsas",
        "imagen": "salsa_soja_recetas_180.jpg"
    },
    {
        "id": 191,
        "nombre": "Salsa Inglesa Recetas de Entonces x 180 ml",
        "descripcion": "Salsa inglesa. Marca Recetas de Entonces. Por unidad de 180 ml.",
        "precio": 0,
        "categoria": "Salsas",
        "imagen": "salsa_inglesa_recetas_180.jpg"
    },
    {
        "id": 192,
        "nombre": "Aceto Balsámico Recetas de Entonces x 250 ml",
        "descripcion": "Aceto balsámico. Marca Recetas de Entonces. Por unidad de 250 ml.",
        "precio": 0,
        "categoria": "Salsas",
        "imagen": "aceto_balsamico_recetas_250.jpg"
    },
    {
        "id": 193,
        "nombre": "Salsa de Soja Bitarwan x 500 ml",
        "descripcion": "Salsa de soja. Marca Bitarwan. Por unidad de 500 ml.",
        "precio": 0,
        "categoria": "Salsas",
        "imagen": "salsa_soja_bitarwan_500.jpg"
    },
    {
        "id": 194,
        "nombre": "Salsa de Soja Bitarwan x 1 lt",
        "descripcion": "Salsa de soja. Marca Bitarwan. Por unidad de 1 litro.",
        "precio": 0,
        "categoria": "Salsas",
        "imagen": "salsa_soja_bitarwan_1lt.jpg"
    },
    {
        "id": 195,
        "nombre": "Tonkatsu Alcaraz Gourmet x 250 ml",
        "descripcion": "Salsa Tonkatsu japonesa. Marca Alcaraz Gourmet. Por unidad de 250 ml.",
        "precio": 0,
        "categoria": "Salsas",
        "imagen": "tonkatsu_alcaraz_250.jpg"
    },
    {
        "id": 196,
        "nombre": "Teriyaki Alcaraz Gourmet x 250 ml",
        "descripcion": "Salsa Teriyaki japonesa. Marca Alcaraz Gourmet. Por unidad de 250 ml.",
        "precio": 0,
        "categoria": "Salsas",
        "imagen": "teriyaki_alcaraz_250.jpg"
    },
    {
        "id": 197,
        "nombre": "Pimiento Jalapeño Intenso Chovi x 60 gr",
        "descripcion": "Pimiento jalapeño intenso. Marca Chovi. Por unidad de 60 gr.",
        "precio": 0,
        "categoria": "Salsas",
        "imagen": "jalapeno_chovi_60.jpg"
    },
    {
        "id": 198,
        "nombre": "Chili Picante Pampagourmet x 200 gr",
        "descripcion": "Salsa chili picante. Marca Pampagourmet. Por unidad de 200 gr.",
        "precio": 0,
        "categoria": "Salsas",
        "imagen": "chili_pampagourmet_200.jpg"
    },
    {
        "id": 199,
        "nombre": "Spicy Mango Pampagourmet x 295 gr",
        "descripcion": "Salsa spicy mango. Marca Pampagourmet. Por unidad de 295 gr.",
        "precio": 0,
        "categoria": "Salsas",
        "imagen": "spicy_mango_pampagourmet_295.jpg"
    },

    # HIERBAS MEDICINALES
    {
        "id": 87,
        "nombre": "Anís Verde",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "anis_verde.jpg"
    },
    {
        "id": 88,
        "nombre": "Alcachofa",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "alcachofa.jpg"
    },
    {
        "id": 89,
        "nombre": "Ajenjo",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "ajenjo.jpg"
    },
    {
        "id": 90,
        "nombre": "Atamisqui",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "atamisqui.jpg"
    },
    {
        "id": 91,
        "nombre": "Altamisa",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "altamisa.jpg"
    },
    {
        "id": 92,
        "nombre": "Artemisa",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "artemisa.jpg"
    },
    {
        "id": 93,
        "nombre": "Acoro",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "acoro.jpg"
    },
    {
        "id": 94,
        "nombre": "Bardana",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "bardana.jpg"
    },
    {
        "id": 95,
        "nombre": "Bolsa de Pastor",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "bolsa_de_pastor.jpg"
    },
    {
        "id": 96,
        "nombre": "Boldo",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "boldo.jpg"
    },
    {
        "id": 97,
        "nombre": "Burro",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "burro.jpg"
    },
    {
        "id": 98,
        "nombre": "Carqueja",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "carqueja.jpg"
    },
    {
        "id": 99,
        "nombre": "Contrayerba",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "contrayerba.jpg"
    },
    {
        "id": 100,
        "nombre": "Congorosa",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "congorosa.jpg"
    },
    {
        "id": 101,
        "nombre": "Corteza de Chañar",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "corteza_chanar.jpg"
    },
    {
        "id": 102,
        "nombre": "Cedrón",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "cedron.jpg"
    },
    {
        "id": 103,
        "nombre": "Ceibo",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "ceibo.jpg"
    },
    {
        "id": 104,
        "nombre": "Cuassia Amarga",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "cuassia_amarga.jpg"
    },
    {
        "id": 105,
        "nombre": "Cola de Caballo",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "cola_de_caballo.jpg"
    },
    {
        "id": 106,
        "nombre": "Cepa Caballo",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "cepa_caballo.jpg"
    },
    {
        "id": 107,
        "nombre": "Cardo Mariano",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "cardo_mariano.jpg"
    },
    {
        "id": 108,
        "nombre": "Cardo Santo",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "cardo_santo.jpg"
    },
    {
        "id": 109,
        "nombre": "Cola de Quirquincho",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "cola_de_quirquincho.jpg"
    },
    {
        "id": 110,
        "nombre": "Diente de León",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "diente_de_leon.jpg"
    },
    {
        "id": 111,
        "nombre": "Doradilla",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "doradilla.jpg"
    },
    {
        "id": 112,
        "nombre": "Eucaliptus",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "eucaliptus.jpg"
    },
    {
        "id": 113,
        "nombre": "Estigma de Maíz",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "estigma_de_maiz.jpg"
    },
    {
        "id": 114,
        "nombre": "Fresno",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "fresno.jpg"
    },
    {
        "id": 115,
        "nombre": "Grataegus",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "grataegus.jpg"
    },
    {
        "id": 116,
        "nombre": "Ginkgo Biloba",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "ginkgo_biloba.jpg"
    },
    {
        "id": 117,
        "nombre": "Hibiscus / Flor de Jamaica",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "hibiscus.jpg"
    },
    {
        "id": 118,
        "nombre": "Hipérico",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "hiperico.jpg"
    },
    {
        "id": 119,
        "nombre": "Hisopo",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "hisopo.jpg"
    },
    {
        "id": 120,
        "nombre": "Incayuyo",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "incayuyo.jpg"
    },
    {
        "id": 121,
        "nombre": "Jarilla",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "jarilla.jpg"
    },
    {
        "id": 122,
        "nombre": "Llantén",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "llanten.jpg"
    },
    {
        "id": 123,
        "nombre": "Lavanda",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "lavanda.jpg"
    },
    {
        "id": 124,
        "nombre": "Melisa",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "melisa.jpg"
    },
    {
        "id": 125,
        "nombre": "Mastuerzo",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "mastuerzo.jpg"
    },
    {
        "id": 126,
        "nombre": "Manzanilla",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "manzanilla.jpg"
    },
    {
        "id": 127,
        "nombre": "Menta",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "menta.jpg"
    },
    {
        "id": 128,
        "nombre": "Marrubio",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "marrubio.jpg"
    },
    {
        "id": 129,
        "nombre": "Marcela",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "marcela.jpg"
    },
    {
        "id": 130,
        "nombre": "Moringa",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "moringa.jpg"
    },
    {
        "id": 131,
        "nombre": "Muérdago",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "muerdago.jpg"
    },
    {
        "id": 132,
        "nombre": "Muña Muña",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "muna_muna.jpg"
    },
    {
        "id": 133,
        "nombre": "Mil Hombres",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "mil_hombres.jpg"
    },
    {
        "id": 134,
        "nombre": "Matico",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "matico.jpg"
    },
    {
        "id": 135,
        "nombre": "Ortiga",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "ortiga.jpg"
    },
    {
        "id": 136,
        "nombre": "Palo Azul",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "palo_azul.jpg"
    },
    {
        "id": 137,
        "nombre": "Pulmonaria",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "pulmonaria.jpg"
    },
    {
        "id": 138,
        "nombre": "Palo Santo",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "palo_santo.jpg"
    },
    {
        "id": 139,
        "nombre": "Palo Amarillo",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "palo_amarillo.jpg"
    },
    {
        "id": 140,
        "nombre": "Pasionaria",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "pasionaria.jpg"
    },
    {
        "id": 141,
        "nombre": "Poleo",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "poleo.jpg"
    },
    {
        "id": 142,
        "nombre": "Peperina",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "peperina.jpg"
    },
    {
        "id": 143,
        "nombre": "Paico",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "paico.jpg"
    },
    {
        "id": 144,
        "nombre": "Rompepiedra",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "rompepiedra.jpg"
    },
    {
        "id": 145,
        "nombre": "Rica Rica",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "rica_rica.jpg"
    },
    {
        "id": 146,
        "nombre": "Ruda",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "ruda.jpg"
    },
    {
        "id": 147,
        "nombre": "Retamilla",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "retamilla.jpg"
    },
    {
        "id": 148,
        "nombre": "Romerillo",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "romerillo.jpg"
    },
    {
        "id": 149,
        "nombre": "Rosa Mosqueta",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "rosa_mosqueta.jpg"
    },
    {
        "id": 150,
        "nombre": "Regaliz",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "regaliz.jpg"
    },
    {
        "id": 151,
        "nombre": "Stevia",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "stevia.jpg"
    },
    {
        "id": 152,
        "nombre": "Sen",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "sen.jpg"
    },
    {
        "id": 153,
        "nombre": "Salvia Blanca",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "salvia_blanca.jpg"
    },
    {
        "id": 154,
        "nombre": "Sombra de Toro",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "sombra_de_toro.jpg"
    },
    {
        "id": 155,
        "nombre": "Suico",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "suico.jpg"
    },
    {
        "id": 156,
        "nombre": "Tusca",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "tusca.jpg"
    },
    {
        "id": 157,
        "nombre": "Verbena",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "verbena.jpg"
    },
    {
        "id": 158,
        "nombre": "Vira Vira",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "vira_vira.jpg"
    },
    {
        "id": 159,
        "nombre": "Yerba de Pollo",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "yerba_de_pollo.jpg"
    },
    {
        "id": 160,
        "nombre": "Zarzaparrilla",
        "descripcion": "Hierba medicinal a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Hierbas Medicinales",
        "imagen": "zarzaparrilla.jpg"
    },

    # DESAYUNO

    # — ALMOHADITAS DE AVENA —
    {
        "id": 65,
        "nombre": "Almohaditas de Avena Frutilla",
        "descripcion": "Almohaditas de avena sabor frutilla a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Desayuno",
        "subcategoria": "Almohaditas de Avena",
        "imagen": "almohaditas_avena_frutilla.jpg"
    },
    {
        "id": 66,
        "nombre": "Almohaditas de Avena Chocolate",
        "descripcion": "Almohaditas de avena sabor chocolate a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Desayuno",
        "subcategoria": "Almohaditas de Avena",
        "imagen": "almohaditas_avena_chocolate.jpg"
    },
    {
        "id": 67,
        "nombre": "Almohaditas de Avena Limón y Chocolate",
        "descripcion": "Almohaditas de avena sabor limón y chocolate a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Desayuno",
        "subcategoria": "Almohaditas de Avena",
        "imagen": "almohaditas_avena_limon_chocolate.jpg"
    },
    {
        "id": 68,
        "nombre": "Almohaditas de Avena Limón",
        "descripcion": "Almohaditas de avena sabor limón a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Desayuno",
        "subcategoria": "Almohaditas de Avena",
        "imagen": "almohaditas_avena_limon.jpg"
    },
    {
        "id": 69,
        "nombre": "Almohaditas de Avena Avellana",
        "descripcion": "Almohaditas de avena sabor avellana a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Desayuno",
        "subcategoria": "Almohaditas de Avena",
        "imagen": "almohaditas_avena_avellana.jpg"
    },

    # — ALMOHADITAS DE ARROZ —
    {
        "id": 70,
        "nombre": "Almohaditas de Arroz Frutilla",
        "descripcion": "Almohaditas de arroz sabor frutilla a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Desayuno",
        "subcategoria": "Almohaditas de Arroz",
        "imagen": "almohaditas_arroz_frutilla.jpg"
    },
    {
        "id": 71,
        "nombre": "Almohaditas de Arroz Limón",
        "descripcion": "Almohaditas de arroz sabor limón a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Desayuno",
        "subcategoria": "Almohaditas de Arroz",
        "imagen": "almohaditas_arroz_limon.jpg"
    },
    {
        "id": 72,
        "nombre": "Almohaditas de Arroz Avellana",
        "descripcion": "Almohaditas de arroz sabor avellana a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Desayuno",
        "subcategoria": "Almohaditas de Arroz",
        "imagen": "almohaditas_arroz_avellana.jpg"
    },
    {
        "id": 73,
        "nombre": "Almohaditas de Arroz Chocolate",
        "descripcion": "Almohaditas de arroz sabor chocolate a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Desayuno",
        "subcategoria": "Almohaditas de Arroz",
        "imagen": "almohaditas_arroz_chocolate.jpg"
    },

    # — OSITOS —
    {
        "id": 74,
        "nombre": "Ositos de Avena",
        "descripcion": "Ositos de avena a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Desayuno",
        "subcategoria": "Ositos",
        "imagen": "ositos_avena.jpg"
    },
    {
        "id": 75,
        "nombre": "Ositos de Frutilla",
        "descripcion": "Ositos sabor frutilla a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Desayuno",
        "subcategoria": "Ositos",
        "imagen": "ositos_frutilla.jpg"
    },

    # — COPOS DE MAÍZ —
    {
        "id": 76,
        "nombre": "Copos de Maíz Azucarados",
        "descripcion": "Copos de maíz azucarados a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Desayuno",
        "subcategoria": "Copos de Maíz",
        "imagen": "copos_maiz_azucarados.jpg"
    },
    {
        "id": 77,
        "nombre": "Copos de Maíz Sin Azúcar",
        "descripcion": "Copos de maíz sin azúcar a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Desayuno",
        "subcategoria": "Copos de Maíz",
        "imagen": "copos_maiz_sin_azucar.jpg"
    },
    {
        "id": 78,
        "nombre": "Copos de Maíz Integral",
        "descripcion": "Copos de maíz integral a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Desayuno",
        "subcategoria": "Copos de Maíz",
        "imagen": "copos_maiz_integral.jpg"
    },

    # — TUTUCAS —
    {
        "id": 79,
        "nombre": "Tutucas con Azúcar",
        "descripcion": "Tutucas con azúcar a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Desayuno",
        "subcategoria": "Tutucas",
        "imagen": "tutucas_con_azucar.jpg"
    },
    {
        "id": 80,
        "nombre": "Tutucas sin Azúcar",
        "descripcion": "Tutucas sin azúcar a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Desayuno",
        "subcategoria": "Tutucas",
        "imagen": "tutucas_sin_azucar.jpg"
    },

    # — OTROS CEREALES DE DESAYUNO —
    {
        "id": 81,
        "nombre": "Anillitos Frutados",
        "descripcion": "Anillitos frutados a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Desayuno",
        "subcategoria": "Otros Cereales",
        "imagen": "anillitos_frutados.jpg"
    },
    {
        "id": 82,
        "nombre": "Quinoa Pop",
        "descripcion": "Quinoa pop a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Desayuno",
        "subcategoria": "Otros Cereales",
        "imagen": "quinoa_pop.jpg"
    },
    {
        "id": 83,
        "nombre": "Crispin de Arroz",
        "descripcion": "Crispin de arroz a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Desayuno",
        "subcategoria": "Otros Cereales",
        "imagen": "crispin_arroz.jpg"
    },
    {
        "id": 84,
        "nombre": "Bastoncito de Salvado",
        "descripcion": "Bastoncitos de salvado a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Desayuno",
        "subcategoria": "Otros Cereales",
        "imagen": "bastoncito_salvado.jpg"
    },
    {
        "id": 85,
        "nombre": "Bolitas de Chocolate",
        "descripcion": "Bolitas de chocolate a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Desayuno",
        "subcategoria": "Otros Cereales",
        "imagen": "bolitas_chocolate.jpg"
    },
    {
        "id": 86,
        "nombre": "Arroz Inflado",
        "descripcion": "Arroz inflado a granel.",
        "precio_100g": 0,
        "precio_kg": 0,
        "categoria": "Desayuno",
        "subcategoria": "Otros Cereales",
        "imagen": "arroz_inflado.jpg"
    },
]


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
    from flask import jsonify
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

    resultados = [p for p in productos if coincide(p)]
    resultados.sort(key=puntaje)

    return jsonify([
        {"nombre": p["nombre"], "categoria": p["categoria"]}
        for p in resultados[:8]
    ])


@app.route('/compras')
def compras():
    busqueda = request.args.get('q', '').lower().strip()
    subcat = request.args.get('subcat', '').strip()
    cat = request.args.get('cat', '').strip()

    if cat:
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

    return render_template('productos.html', productos=resultados, titulo=titulo)


if __name__ == '__main__':
    app.run(debug=True)