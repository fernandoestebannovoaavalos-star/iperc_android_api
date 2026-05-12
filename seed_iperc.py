from app import create_app, db
from app.models import Area, Actividad, TipoPeligro, PeligroBase

app = create_app()

DATA = [
    ("Electricidad","Instalaciones eléctricas","Eléctrico","Contacto eléctrico directo con cables energizados","Electrocución / paro cardíaco",4,4,16,"MODERADO","EPP dieléctrico (guantes, botas, casco). Bloqueo y etiquetado (LOTO). Verificar ausencia de tensión con tester antes de trabajar.",2,3,6,"TOLERABLE","Supervisor Eléctrico","DS 005-2012-TR Art.77"),
    ("Electricidad","Instalaciones eléctricas","Eléctrico","Contacto con tableros eléctricos sin señalización","Quemaduras / electrocución",3,4,12,"MODERADO","Señalizar tableros. Mantener distancia de seguridad. Solo personal autorizado.",2,3,6,"TOLERABLE","Supervisor Eléctrico","RM 111-2013-MEM"),
    ("Electricidad","Instalaciones eléctricas","Eléctrico","Uso de herramientas eléctricas defectuosas","Cortocircuito / incendio / electrocución",3,3,9,"MODERADO","Inspección previa de herramientas. Mantenimiento preventivo. Retirar herramientas en mal estado.",2,2,4,"TRIVIAL","Supervisor Eléctrico","DS 005-2012-TR"),
    ("Electricidad","Instalaciones eléctricas","Mecánico","Cortes con herramientas de corte (alicates, destornilladores)","Laceraciones en manos / dedos",3,2,6,"TOLERABLE","Uso de guantes de corte resistente. Procedimiento de uso seguro de herramientas.",2,1,2,"TRIVIAL","Supervisor Eléctrico","Ley 29783"),
    ("Electricidad","Instalaciones eléctricas","Físico","Exposición a arco eléctrico","Quemaduras graves / ceguera temporal",2,4,8,"TOLERABLE","Careta facial de arco eléctrico. Ropa ignífuga. Procedimiento de trabajo en caliente.",1,3,3,"TRIVIAL","Supervisor Eléctrico","NTP 370.053"),
    ("Aire Acondicionado","Instalación de equipos A/C","Mecánico","Caída de equipos o unidades condensadoras durante maniobra","Golpes graves / aplastamiento",3,4,12,"MODERADO","Uso de eslingas certificadas. Señalizar área. Personal capacitado en maniobras.",2,3,6,"TOLERABLE","Supervisor Mecánico","DS 005-2012-TR"),
    ("Aire Acondicionado","Instalación de equipos A/C","Químico","Manipulación de refrigerantes (R-410A, R-22)","Inhalación / quemaduras por frío / daño ambiental",3,3,9,"MODERADO","EPP (guantes criogénicos, lentes). Ventilación del área. Certificación F-GAS.",2,2,4,"TRIVIAL","Supervisor Mecánico","DS 003-2017-MINAM"),
    ("Aire Acondicionado","Instalación de equipos A/C","Eléctrico","Conexión eléctrica de unidades sin verificación de tensión","Electrocución / cortocircuito",3,4,12,"MODERADO","LOTO. Verificar tensión con multímetro. Solo electricistas certificados.",2,3,6,"TOLERABLE","Supervisor Eléctrico","RM 111-2013-MEM"),
    ("Aire Acondicionado","Instalación de equipos A/C","Ergonómico","Levantamiento manual de unidades pesadas (>25 kg)","Lumbalgia / hernias discales",4,2,8,"TOLERABLE","Uso de polipasto o carretilla. Técnica de levantamiento correcto. Máx. 25 kg por persona.",2,2,4,"TRIVIAL","Supervisor Mecánico","RM 375-2008-TR"),
    ("Aire Acondicionado","Instalación de equipos A/C","Físico","Trabajo en espacios reducidos (falso techo, ductos)","Claustrofobia / golpes / lesiones",3,2,6,"TOLERABLE","Permiso de trabajo en espacio confinado. EPP. Comunicación constante.",2,1,2,"TRIVIAL","Supervisor Mecánico","DS 005-2012-TR"),
    ("Redes y Cableado","Tendido de cables de red","Mecánico","Caída a distinto nivel al usar escalera","Fracturas / traumatismo craneal",4,3,12,"MODERADO","Uso de escalera certificada anclada. Zapatos antideslizantes. Apoyo de segundo trabajador.",2,2,4,"TRIVIAL","Supervisor de Redes","DS 005-2012-TR"),
    ("Redes y Cableado","Tendido de cables de red","Físico","Posturas forzadas al trabajar en falso techo","Cervicalgia / lumbalgia",4,2,8,"TOLERABLE","Pausas activas cada 45 min. Rotación de personal. Capacitación ergonómica.",2,1,2,"TRIVIAL","Supervisor de Redes","RM 375-2008-TR"),
    ("Redes y Cableado","Tendido de cables de red","Mecánico","Cortes con herramienta de ponchado y tijeras","Laceraciones en manos",3,2,6,"TOLERABLE","Guantes de protección mecánica. Capacitación en uso de herramientas.",2,1,2,"TRIVIAL","Supervisor de Redes","Ley 29783"),
    ("Redes y Cableado","Instalación de antenas y equipos","Eléctrico","Interferencia con instalaciones eléctricas existentes","Electrocución / cortocircuito",2,4,8,"TOLERABLE","Plano eléctrico actualizado. Identificar circuitos. Coordinación con electricista.",1,3,3,"TRIVIAL","Supervisor de Redes","RM 111-2013-MEM"),
    ("Redes y Cableado","Instalación de antenas y equipos","Físico","Exposición a radiación de antenas Wi-Fi activas","Efectos biológicos por exposición prolongada",2,2,4,"TRIVIAL","Apagar equipo durante instalación. Tiempo máximo de exposición definido.",1,1,1,"TRIVIAL","Supervisor de Redes","DS 038-2003-MTC"),
    ("Albañilería","Preparación y vaciado de concreto","Físico","Exposición a polvo de cemento (sílice cristalina)","Silicosis / enfermedades respiratorias",4,3,12,"MODERADO","Respirador N95 o superior. Humedecer área. Rotación de personal.",2,2,4,"TRIVIAL","Maestro de Obra","DS 005-2012-TR"),
    ("Albañilería","Preparación y vaciado de concreto","Químico","Contacto de cemento fresco con piel y ojos","Quemaduras químicas / dermatitis",4,2,8,"TOLERABLE","Guantes de nitrilo, lentes de seguridad, ropa de trabajo. Lavado inmediato.",2,1,2,"TRIVIAL","Maestro de Obra","Ley 29783"),
    ("Albañilería","Preparación y vaciado de concreto","Mecánico","Atrapamiento en mezcladora de concreto","Amputación / aplastamiento",2,4,8,"TOLERABLE","Guarda de seguridad en mezcladora. Procedimiento de uso. Nunca introducir manos.",1,4,4,"TRIVIAL","Maestro de Obra","DS 005-2012-TR"),
    ("Albañilería","Levantamiento de muros y tabiques","Mecánico","Caída de bloques o ladrillos sobre operarios","Fracturas / traumatismo craneal",3,3,9,"MODERADO","Casco de seguridad obligatorio. Correcta estiba de materiales. Señalización de área.",2,2,4,"TRIVIAL","Maestro de Obra","DS 005-2012-TR"),
    ("Albañilería","Levantamiento de muros y tabiques","Ergonómico","Sobreesfuerzo por levantamiento de ladrillos repetitivo","Lumbalgia / lesiones musculoesqueléticas",4,2,8,"TOLERABLE","Rotación de tareas. Uso de carretilla. Límite de peso 25 kg.",2,1,2,"TRIVIAL","Maestro de Obra","RM 375-2008-TR"),
    ("Albañilería","Levantamiento de muros y tabiques","Físico","Exposición a ruido de herramientas (amoladora, martillo)","Hipoacusia / pérdida auditiva",4,2,8,"TOLERABLE","Tapones auditivos. Tiempo máx. de exposición. Rotación de personal.",2,1,2,"TRIVIAL","Maestro de Obra","RM 375-2008-TR"),
    ("Albañilería","Tarrajeo y enlucido","Físico","Proyección de material de tarrajeo a ojos","Conjuntivitis / lesión ocular",4,2,8,"TOLERABLE","Lentes de seguridad. Pantalla facial. Posición correcta al aplicar.",2,1,2,"TRIVIAL","Maestro de Obra","DS 005-2012-TR"),
    ("Enchapado","Corte y colocación de cerámicos","Mecánico","Cortes con amoladora y cortadora de cerámicos","Laceraciones graves en manos / ojos",4,3,12,"MODERADO","Guantes de corte Nivel 5. Lentes de seguridad. Disco de corte en buen estado.",2,2,4,"TRIVIAL","Supervisor de Acabados","DS 005-2012-TR"),
    ("Enchapado","Corte y colocación de cerámicos","Físico","Exposición a polvo de corte de cerámica (sílice)","Silicosis / irritación vías respiratorias",4,3,12,"MODERADO","Respirador N95. Corte húmedo. Ventilación del área.",2,2,4,"TRIVIAL","Supervisor de Acabados","DS 005-2012-TR"),
    ("Enchapado","Corte y colocación de cerámicos","Ergonómico","Postura de cuclillas prolongada al enchapar piso","Tendinitis rodilla / lumbalgia",4,2,8,"TOLERABLE","Rodilleras de protección. Pausas activas cada 30 min. Rotación de personal.",2,1,2,"TRIVIAL","Supervisor de Acabados","RM 375-2008-TR"),
    ("Enchapado","Aplicación de adhesivos y fraguas","Químico","Inhalación de vapores de pegamento o solventes","Intoxicación / daño hepático",3,3,9,"MODERADO","Respirador con filtro para vapores orgánicos. Ventilación forzada. Descansos al aire libre.",2,2,4,"TRIVIAL","Supervisor de Acabados","DS 005-2012-TR"),
    ("Enchapado","Aplicación de adhesivos y fraguas","Mecánico","Golpe con herramienta de enchapado (llana, martillo)","Contusiones / fracturas",3,2,6,"TOLERABLE","EPP estándar. Orden y limpieza del área de trabajo. Distancia entre operarios.",2,1,2,"TRIVIAL","Supervisor de Acabados","Ley 29783"),
    ("Almacén","Recepción y despacho de materiales","Mecánico","Caída de materiales apilados incorrectamente","Aplastamiento / contusiones",3,3,9,"MODERADO","Estiba correcta (máx. 1.80m). Señalizar pasillos. Rumas estables.",2,2,4,"TRIVIAL","Encargado de Almacén","DS 005-2012-TR"),
    ("Almacén","Recepción y despacho de materiales","Ergonómico","Levantamiento manual de cargas pesadas (>25 kg)","Lumbalgia / hernias",4,2,8,"TOLERABLE","Carretillas y apiladores. Técnica de levantamiento seguro. Trabajo en equipo.",2,1,2,"TRIVIAL","Encargado de Almacén","RM 375-2008-TR"),
    ("Almacén","Recepción y despacho de materiales","Mecánico","Atropellamiento por montacargas o transpaleta","Lesiones graves / muerte",2,4,8,"TOLERABLE","Señalización de pasillos. Limitador de velocidad. Prioridad al peatón.",1,3,3,"TRIVIAL","Encargado de Almacén","DS 005-2012-TR"),
    ("Almacén","Almacenamiento de productos químicos","Químico","Derrame de productos químicos (pinturas, solventes, aditivos)","Intoxicación / incendio / explosión",3,4,12,"MODERADO","Hoja de seguridad (MSDS) disponible. Almacenamiento separado por compatibilidad. Kit anti-derrame.",2,3,6,"TOLERABLE","Encargado de Almacén","DS 005-2012-TR"),
    ("Almacén","Almacenamiento de productos químicos","Físico","Exposición a vapores de solventes en almacén cerrado","Intoxicación crónica / daño neurológico",3,3,9,"MODERADO","Ventilación natural y forzada. Respirador con filtro. Tiempo limitado de exposición.",2,2,4,"TRIVIAL","Encargado de Almacén","DS 005-2012-TR"),
    ("Pintura","Preparación de superficies","Físico","Inhalación de polvo al lijar paredes y superficies","Neumoconiosis / irritación respiratoria",4,3,12,"MODERADO","Respirador N95. Humedecer superficie antes de lijar. Ventilación del área.",2,2,4,"TRIVIAL","Supervisor de Pintores","DS 005-2012-TR"),
    ("Pintura","Preparación de superficies","Mecánico","Proyección de partículas al lijar","Lesión ocular / heridas en rostro",4,2,8,"TOLERABLE","Lentes de seguridad / pantalla facial. Señalización del área.",2,1,2,"TRIVIAL","Supervisor de Pintores","DS 005-2012-TR"),
    ("Pintura","Aplicación de pintura","Químico","Inhalación de vapores de pintura, disolvente y barniz","Intoxicación aguda / crónica / daño hepático",4,3,12,"MODERADO","Respirador con filtro orgánico. Ventilación forzada. Pausas fuera del área.",2,2,4,"TRIVIAL","Supervisor de Pintores","DS 005-2012-TR"),
    ("Pintura","Aplicación de pintura","Químico","Contacto de pintura y solventes con piel","Dermatitis / quemaduras químicas",4,2,8,"TOLERABLE","Guantes de nitrilo / neopreno. Ropa de trabajo. Lavado con agua abundante.",2,1,2,"TRIVIAL","Supervisor de Pintores","DS 005-2012-TR"),
    ("Pintura","Aplicación de pintura en altura","Mecánico","Caída desde andamio o borriqueta al pintar en altura","Fracturas graves / muerte",3,4,12,"MODERADO","Andamio certificado con rodapiés y barandas. Arnés de seguridad. Inspección diaria.",1,3,3,"TRIVIAL","Supervisor de Pintores","G-050 Seguridad en Construcción"),
    ("Pintura","Aplicación de pintura","Físico","Exposición prolongada al ruido de compresor de pintura","Hipoacusia",3,2,6,"TOLERABLE","Tapones auditivos. Rotación de personal. Alejarse del compresor en descanso.",2,1,2,"TRIVIAL","Supervisor de Pintores","RM 375-2008-TR"),
    ("Trabajos en Altura","Instalación de estructura de ascensor","Mecánico","Caída de personas desde hueco del ascensor (>2m)","Muerte / lesiones gravísimas",4,4,16,"MODERADO","Uso obligatorio de arnés con línea de vida. Tarjeta de trabajo en altura. Red de seguridad.",1,4,4,"TRIVIAL","Supervisor de Altura","G-050 Seguridad en Construcción"),
    ("Trabajos en Altura","Instalación de estructura de ascensor","Mecánico","Caída de herramientas u objetos al vacío (efecto péndulo)","Muerte / lesiones a terceros",4,4,16,"MODERADO","Casco obligatorio. Bolsa portaherramientas. Señalizar y acordonar área inferior.",2,4,8,"TOLERABLE","Supervisor de Altura","G-050 Seguridad en Construcción"),
    ("Trabajos en Altura","Instalación de estructura de ascensor","Mecánico","Colapso de andamio o plataforma de trabajo","Muerte / lesiones gravísimas",2,4,8,"TOLERABLE","Andamio certificado. Inspección por supervisor antes de usar. Montaje por personal calificado.",1,4,4,"TRIVIAL","Supervisor de Altura","DS 005-2012-TR"),
    ("Trabajos en Altura","Instalación de estructura de ascensor","Eléctrico","Contacto con instalaciones eléctricas en el hueco","Electrocución",3,4,12,"MODERADO","Mapa eléctrico del edificio. LOTO. Trabajo coordinado con electricista.",1,4,4,"TRIVIAL","Supervisor de Altura","RM 111-2013-MEM"),
    ("Trabajos en Altura","Izaje de componentes del ascensor","Mecánico","Fallo de aparejo o grúa durante maniobra de izaje","Aplastamiento / muerte",2,4,8,"TOLERABLE","Certificación de aparejo. Plan de izaje aprobado. Señalizar área. Radio de caída libre despejado.",1,4,4,"TRIVIAL","Supervisor de Altura","DS 005-2012-TR"),
    ("Trabajos en Altura","Izaje de componentes del ascensor","Mecánico","Golpe por oscilación de carga durante izaje","Lesiones graves / muerte",2,4,8,"TOLERABLE","Uso de vientos (cuerdas guía). Personal entrenado. Comunicación por radio.",1,3,3,"TRIVIAL","Supervisor de Altura","DS 005-2012-TR"),
    ("Trabajos en Altura","Instalación de cabina de ascensor","Psicosocial","Estrés y fatiga por trabajos en hueco (espacio confinado en altura)","Pérdida de concentración / accidente",3,3,9,"MODERADO","Rotación de personal. Pausas programadas. Psicólogo disponible. Vigilancia de síntomas.",2,2,4,"TRIVIAL","Supervisor de Altura","DS 005-2012-TR"),
    ("Trabajos en Altura","Instalación de cabina de ascensor","Físico","Exposición a ruido intenso de taladro y soldadura en espacio cerrado","Hipoacusia / acúfenos",4,2,8,"TOLERABLE","Tapones auditivos de doble protección. Tiempo máx. de exposición 30 min continuos.",2,1,2,"TRIVIAL","Supervisor de Altura","RM 375-2008-TR"),
    ("General","Transporte interno en obra","Mecánico","Atropellamiento por vehículo de obra","Lesiones graves / muerte",3,4,12,"MODERADO","Velocidad máx. 10 km/h en obra. Señalización vial interna. Vigías en maniobras.",1,4,4,"TRIVIAL","Jefe de Obra","G-050"),
    ("General","Trabajos en general","Físico","Exposición a calor extremo (obra a cielo abierto)","Golpe de calor / deshidratación",4,2,8,"TOLERABLE","Hidratación cada 20 min. Sombra disponible. Monitoreo de temperatura. Ropa adecuada.",2,1,2,"TRIVIAL","Maestro de Obra","DS 005-2012-TR"),
    ("General","Trabajos en general","Psicosocial","Estrés laboral por presión de plazos de entrega","Accidente por distracción / burnout",3,2,6,"TOLERABLE","Pausas programadas. Comunicación asertiva. Distribución equitativa de carga.",2,1,2,"TRIVIAL","Jefe de Obra","Ley 29783"),
    ("General","Emergencias","Físico","Incendio en almacén o zona de trabajo","Quemaduras / asfixia / muerte",2,4,8,"TOLERABLE","Extintores PQS señalizados. Plan de emergencia. Simulacros semestrales. Rutas de evacuación.",1,3,3,"TRIVIAL","Jefe de Seguridad","DS 005-2012-TR"),
]

with app.app_context():
    areas = {}
    actividades = {}
    tipos = {}

    for row in DATA:
        area_nombre = row[0]
        act_nombre = row[1]
        tipo_nombre = row[2]

        if area_nombre not in areas:
            a = Area(nombre=area_nombre)
            db.session.add(a)
            db.session.flush()
            areas[area_nombre] = a.id

        key_act = (area_nombre, act_nombre)
        if key_act not in actividades:
            act = Actividad(nombre=act_nombre, area_id=areas[area_nombre])
            db.session.add(act)
            db.session.flush()
            actividades[key_act] = act.id

        if tipo_nombre not in tipos:
            t = TipoPeligro(nombre=tipo_nombre)
            db.session.add(t)
            db.session.flush()
            tipos[tipo_nombre] = t.id

        peligro = PeligroBase(
            actividad_id=actividades[key_act],
            tipo_peligro_id=tipos[tipo_nombre],
            descripcion=row[3],
            riesgo_consecuencia=row[4],
            p_sin=row[5],
            s_sin=row[6],
            nivel_sin=row[8],
            medidas_control=row[9],
            p_con=row[10],
            s_con=row[11],
            nivel_con=row[13],
            responsable=row[14],
            requisito_legal=row[15]
        )
        db.session.add(peligro)

    db.session.commit()
    print(f"✓ {len(DATA)} peligros importados correctamente")
    print(f"✓ {len(areas)} áreas creadas")
    print(f"✓ {len(actividades)} actividades creadas")
    print(f"✓ {len(tipos)} tipos de peligro creados")
