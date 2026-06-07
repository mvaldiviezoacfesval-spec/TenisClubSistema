import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get('DB_PATH', os.path.join(BASE_DIR, 'tenis_club.db'))

def get_db():
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    # --- SOCIOS ---
    c.execute('''CREATE TABLE IF NOT EXISTS socios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT UNIQUE NOT NULL,
        nombres TEXT NOT NULL,
        apellidos TEXT NOT NULL,
        cedula TEXT UNIQUE NOT NULL,
        email TEXT,
        telefono TEXT,
        direccion TEXT,
        categoria TEXT DEFAULT 'Activo',
        fecha_ingreso TEXT NOT NULL,
        fecha_nacimiento TEXT,
        estado TEXT DEFAULT 'Activo',
        cuota_mensual REAL DEFAULT 30.00,
        observaciones TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    )''')

    # --- PLAN DE CUENTAS ---
    c.execute('''CREATE TABLE IF NOT EXISTS plan_cuentas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT UNIQUE NOT NULL,
        nombre TEXT NOT NULL,
        tipo TEXT NOT NULL,
        naturaleza TEXT NOT NULL,
        nivel INTEGER DEFAULT 1,
        cuenta_padre_id INTEGER,
        activa INTEGER DEFAULT 1,
        FOREIGN KEY(cuenta_padre_id) REFERENCES plan_cuentas(id)
    )''')

    # --- ASIENTOS CONTABLES ---
    c.execute('''CREATE TABLE IF NOT EXISTS asientos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero TEXT UNIQUE NOT NULL,
        fecha TEXT NOT NULL,
        concepto TEXT NOT NULL,
        tipo TEXT DEFAULT 'manual',
        referencia_id INTEGER,
        referencia_tipo TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS asiento_detalles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        asiento_id INTEGER NOT NULL,
        cuenta_id INTEGER NOT NULL,
        descripcion TEXT,
        debe REAL DEFAULT 0,
        haber REAL DEFAULT 0,
        FOREIGN KEY(asiento_id) REFERENCES asientos(id),
        FOREIGN KEY(cuenta_id) REFERENCES plan_cuentas(id)
    )''')

    # --- PROVEEDORES ---
    c.execute('''CREATE TABLE IF NOT EXISTS proveedores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ruc TEXT UNIQUE NOT NULL,
        razon_social TEXT NOT NULL,
        nombre_comercial TEXT,
        email TEXT,
        telefono TEXT,
        direccion TEXT,
        tipo TEXT DEFAULT 'Proveedor',
        estado TEXT DEFAULT 'Activo'
    )''')

    # --- CLIENTES ---
    c.execute('''CREATE TABLE IF NOT EXISTS clientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ruc_cedula TEXT UNIQUE NOT NULL,
        razon_social TEXT NOT NULL,
        email TEXT,
        telefono TEXT,
        direccion TEXT,
        tipo TEXT DEFAULT 'Cliente',
        estado TEXT DEFAULT 'Activo'
    )''')

    # --- FACTURAS VENTA ---
    c.execute('''CREATE TABLE IF NOT EXISTS facturas_venta (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero TEXT UNIQUE NOT NULL,
        fecha TEXT NOT NULL,
        cliente_id INTEGER,
        cliente_nombre TEXT NOT NULL,
        subtotal REAL NOT NULL,
        iva REAL DEFAULT 0,
        total REAL NOT NULL,
        estado TEXT DEFAULT 'Emitida',
        observaciones TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY(cliente_id) REFERENCES clientes(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS factura_venta_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        factura_id INTEGER NOT NULL,
        descripcion TEXT NOT NULL,
        cantidad REAL NOT NULL,
        precio_unitario REAL NOT NULL,
        descuento REAL DEFAULT 0,
        subtotal REAL NOT NULL,
        FOREIGN KEY(factura_id) REFERENCES facturas_venta(id)
    )''')

    # --- FACTURAS COMPRA ---
    c.execute('''CREATE TABLE IF NOT EXISTS facturas_compra (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero TEXT NOT NULL,
        fecha TEXT NOT NULL,
        proveedor_id INTEGER,
        proveedor_nombre TEXT NOT NULL,
        subtotal REAL NOT NULL,
        iva REAL DEFAULT 0,
        total REAL NOT NULL,
        estado TEXT DEFAULT 'Registrada',
        observaciones TEXT,
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY(proveedor_id) REFERENCES proveedores(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS factura_compra_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        factura_id INTEGER NOT NULL,
        descripcion TEXT NOT NULL,
        cantidad REAL NOT NULL,
        precio_unitario REAL NOT NULL,
        subtotal REAL NOT NULL,
        FOREIGN KEY(factura_id) REFERENCES facturas_compra(id)
    )''')

    # --- NOTAS DE CREDITO ---
    c.execute('''CREATE TABLE IF NOT EXISTS notas_credito (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero TEXT UNIQUE NOT NULL,
        fecha TEXT NOT NULL,
        factura_ref TEXT,
        cliente_nombre TEXT NOT NULL,
        motivo TEXT NOT NULL,
        total REAL NOT NULL,
        tipo TEXT DEFAULT 'Venta',
        estado TEXT DEFAULT 'Emitida',
        created_at TEXT DEFAULT (datetime('now'))
    )''')

    # --- CUOTAS DE SOCIOS ---
    c.execute('''CREATE TABLE IF NOT EXISTS cuotas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        socio_id INTEGER NOT NULL,
        periodo TEXT NOT NULL,
        fecha_vencimiento TEXT NOT NULL,
        monto REAL NOT NULL,
        mora REAL DEFAULT 0,
        total REAL NOT NULL,
        estado TEXT DEFAULT 'Pendiente',
        fecha_pago TEXT,
        metodo_pago TEXT,
        comprobante TEXT,
        FOREIGN KEY(socio_id) REFERENCES socios(id)
    )''')

    # --- CUENTAS POR COBRAR ---
    c.execute('''CREATE TABLE IF NOT EXISTS cuentas_cobrar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero TEXT NOT NULL,
        fecha_emision TEXT NOT NULL,
        fecha_vencimiento TEXT NOT NULL,
        cliente_nombre TEXT NOT NULL,
        concepto TEXT NOT NULL,
        monto_original REAL NOT NULL,
        monto_pagado REAL DEFAULT 0,
        saldo REAL NOT NULL,
        estado TEXT DEFAULT 'Pendiente',
        referencia TEXT
    )''')
    _add_column_if_missing(c, 'cuentas_cobrar', 'referencia_tipo', 'TEXT')
    _add_column_if_missing(c, 'cuentas_cobrar', 'referencia_id', 'INTEGER')

    # --- CUENTAS POR PAGAR ---
    c.execute('''CREATE TABLE IF NOT EXISTS cuentas_pagar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero TEXT NOT NULL,
        fecha_emision TEXT NOT NULL,
        fecha_vencimiento TEXT NOT NULL,
        proveedor_nombre TEXT NOT NULL,
        concepto TEXT NOT NULL,
        monto_original REAL NOT NULL,
        monto_pagado REAL DEFAULT 0,
        saldo REAL NOT NULL,
        estado TEXT DEFAULT 'Pendiente',
        referencia TEXT
    )''')
    _add_column_if_missing(c, 'cuentas_pagar', 'referencia_tipo', 'TEXT')
    _add_column_if_missing(c, 'cuentas_pagar', 'referencia_id', 'INTEGER')

    # --- MOVIMIENTOS BANCARIOS ---
    c.execute('''CREATE TABLE IF NOT EXISTS movimientos_bancarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cuenta_bancaria TEXT NOT NULL,
        fecha TEXT NOT NULL,
        descripcion TEXT NOT NULL,
        tipo TEXT NOT NULL,
        monto REAL NOT NULL,
        saldo_banco REAL,
        referencia TEXT,
        conciliado INTEGER DEFAULT 0,
        asiento_id INTEGER,
        FOREIGN KEY(asiento_id) REFERENCES asientos(id)
    )''')

    # --- INVENTARIO ---
    c.execute('''CREATE TABLE IF NOT EXISTS inventario (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT UNIQUE NOT NULL,
        nombre TEXT NOT NULL,
        descripcion TEXT,
        categoria TEXT,
        unidad TEXT DEFAULT 'Unidad',
        stock_actual REAL DEFAULT 0,
        stock_minimo REAL DEFAULT 5,
        precio_costo REAL DEFAULT 0,
        precio_venta REAL DEFAULT 0,
        ubicacion TEXT,
        estado TEXT DEFAULT 'Activo'
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS movimientos_inventario (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        producto_id INTEGER NOT NULL,
        fecha TEXT NOT NULL,
        tipo TEXT NOT NULL,
        cantidad REAL NOT NULL,
        precio_unitario REAL DEFAULT 0,
        referencia TEXT,
        observaciones TEXT,
        stock_resultante REAL,
        FOREIGN KEY(producto_id) REFERENCES inventario(id)
    )''')

    # --- EMPLEADOS ---
    c.execute('''CREATE TABLE IF NOT EXISTS empleados (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codigo TEXT UNIQUE NOT NULL,
        nombres TEXT NOT NULL,
        apellidos TEXT NOT NULL,
        cedula TEXT UNIQUE NOT NULL,
        cargo TEXT NOT NULL,
        departamento TEXT,
        salario_base REAL NOT NULL,
        fecha_ingreso TEXT NOT NULL,
        tipo_contrato TEXT DEFAULT 'Indefinido',
        estado TEXT DEFAULT 'Activo',
        email TEXT,
        telefono TEXT,
        cuenta_bancaria TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS roles_pago (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empleado_id INTEGER NOT NULL,
        periodo TEXT NOT NULL,
        salario_base REAL NOT NULL,
        horas_extra REAL DEFAULT 0,
        valor_horas_extra REAL DEFAULT 0,
        bonos REAL DEFAULT 0,
        iess_personal REAL DEFAULT 0,
        iess_patronal REAL DEFAULT 0,
        impuesto_renta REAL DEFAULT 0,
        otros_descuentos REAL DEFAULT 0,
        liquido_recibir REAL NOT NULL,
        estado TEXT DEFAULT 'Borrador',
        fecha_pago TEXT,
        FOREIGN KEY(empleado_id) REFERENCES empleados(id)
    )''')

    # --- PROFORMAS ---
    c.execute('''CREATE TABLE IF NOT EXISTS proformas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero TEXT UNIQUE NOT NULL,
        fecha TEXT NOT NULL,
        validez_dias INTEGER DEFAULT 30,
        cliente_nombre TEXT NOT NULL,
        cliente_email TEXT,
        objeto TEXT,
        subtotal REAL NOT NULL,
        iva REAL DEFAULT 0,
        total REAL NOT NULL,
        estado TEXT DEFAULT 'Borrador',
        observaciones TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS proforma_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        proforma_id INTEGER NOT NULL,
        descripcion TEXT NOT NULL,
        cantidad REAL NOT NULL,
        precio_unitario REAL NOT NULL,
        subtotal REAL NOT NULL,
        FOREIGN KEY(proforma_id) REFERENCES proformas(id)
    )''')

    # --- TORNEOS Y EVENTOS ---
    c.execute('''CREATE TABLE IF NOT EXISTS torneos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        tipo TEXT DEFAULT 'Torneo',
        fecha_inicio TEXT NOT NULL,
        fecha_fin TEXT NOT NULL,
        descripcion TEXT,
        presupuesto REAL DEFAULT 0,
        estado TEXT DEFAULT 'Planificado'
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS torneo_transacciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        torneo_id INTEGER NOT NULL,
        fecha TEXT NOT NULL,
        tipo TEXT NOT NULL,
        concepto TEXT NOT NULL,
        monto REAL NOT NULL,
        referencia TEXT,
        FOREIGN KEY(torneo_id) REFERENCES torneos(id)
    )''')

    # --- DECLARACIONES SRI ---
    c.execute('''CREATE TABLE IF NOT EXISTS declaraciones_sri (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        periodo TEXT NOT NULL,
        tipo TEXT NOT NULL,
        formulario TEXT,
        ventas_gravadas REAL DEFAULT 0,
        ventas_exentas REAL DEFAULT 0,
        compras_con_credito REAL DEFAULT 0,
        iva_cobrado REAL DEFAULT 0,
        iva_pagado REAL DEFAULT 0,
        iva_pagar REAL DEFAULT 0,
        retenciones_emitidas REAL DEFAULT 0,
        retenciones_recibidas REAL DEFAULT 0,
        estado TEXT DEFAULT 'Borrador',
        fecha_declaracion TEXT,
        created_at TEXT DEFAULT (datetime('now'))
    )''')

    conn.commit()

    # Insertar plan de cuentas base si está vacío
    c.execute("SELECT COUNT(*) FROM plan_cuentas")
    if c.fetchone()[0] == 0:
        _insertar_plan_cuentas(c)
        conn.commit()

    conn.close()

def _add_column_if_missing(c, table, column, definition):
    cols = [row[1] for row in c.execute(f"PRAGMA table_info({table})").fetchall()]
    if column not in cols:
        c.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

def _insertar_plan_cuentas(c):
    cuentas = [
        # ACTIVOS
        ('1', 'ACTIVOS', 'Activo', 'Deudora', 1, None),
        ('1.1', 'ACTIVO CORRIENTE', 'Activo', 'Deudora', 2, None),
        ('1.1.01', 'Caja', 'Activo', 'Deudora', 3, None),
        ('1.1.02', 'Bancos', 'Activo', 'Deudora', 3, None),
        ('1.1.03', 'Cuentas por Cobrar Socios', 'Activo', 'Deudora', 3, None),
        ('1.1.04', 'Cuentas por Cobrar Clientes', 'Activo', 'Deudora', 3, None),
        ('1.1.05', 'Inventario de Mercadería', 'Activo', 'Deudora', 3, None),
        ('1.1.06', 'Anticipo a Proveedores', 'Activo', 'Deudora', 3, None),
        ('1.1.07', 'IVA Compras (Crédito Fiscal)', 'Activo', 'Deudora', 3, None),
        ('1.2', 'ACTIVO NO CORRIENTE', 'Activo', 'Deudora', 2, None),
        ('1.2.01', 'Propiedad Planta y Equipo', 'Activo', 'Deudora', 3, None),
        ('1.2.02', 'Dep. Acumulada PPE', 'Activo', 'Acreedora', 3, None),
        # PASIVOS
        ('2', 'PASIVOS', 'Pasivo', 'Acreedora', 1, None),
        ('2.1', 'PASIVO CORRIENTE', 'Pasivo', 'Acreedora', 2, None),
        ('2.1.01', 'Cuentas por Pagar Proveedores', 'Pasivo', 'Acreedora', 3, None),
        ('2.1.02', 'IVA en Ventas (Por Pagar)', 'Pasivo', 'Acreedora', 3, None),
        ('2.1.03', 'Retenciones en Fuente por Pagar', 'Pasivo', 'Acreedora', 3, None),
        ('2.1.04', 'IESS por Pagar', 'Pasivo', 'Acreedora', 3, None),
        ('2.1.05', 'Sueldos por Pagar', 'Pasivo', 'Acreedora', 3, None),
        ('2.1.06', 'Décimo Tercero por Pagar', 'Pasivo', 'Acreedora', 3, None),
        ('2.1.07', 'Décimo Cuarto por Pagar', 'Pasivo', 'Acreedora', 3, None),
        # PATRIMONIO
        ('3', 'PATRIMONIO', 'Patrimonio', 'Acreedora', 1, None),
        ('3.1.01', 'Capital Social', 'Patrimonio', 'Acreedora', 3, None),
        ('3.1.02', 'Reservas', 'Patrimonio', 'Acreedora', 3, None),
        ('3.1.03', 'Resultado del Ejercicio', 'Patrimonio', 'Acreedora', 3, None),
        # INGRESOS
        ('4', 'INGRESOS', 'Ingreso', 'Acreedora', 1, None),
        ('4.1.01', 'Ingresos por Cuotas de Socios', 'Ingreso', 'Acreedora', 3, None),
        ('4.1.02', 'Ingresos por Torneos', 'Ingreso', 'Acreedora', 3, None),
        ('4.1.03', 'Ingresos por Servicios', 'Ingreso', 'Acreedora', 3, None),
        ('4.1.04', 'Ingresos por Venta de Artículos', 'Ingreso', 'Acreedora', 3, None),
        ('4.1.05', 'Otros Ingresos', 'Ingreso', 'Acreedora', 3, None),
        # GASTOS
        ('5', 'GASTOS', 'Gasto', 'Deudora', 1, None),
        ('5.1.01', 'Sueldos y Salarios', 'Gasto', 'Deudora', 3, None),
        ('5.1.02', 'Aporte Patronal IESS', 'Gasto', 'Deudora', 3, None),
        ('5.1.03', 'Servicios Básicos', 'Gasto', 'Deudora', 3, None),
        ('5.1.04', 'Mantenimiento y Reparaciones', 'Gasto', 'Deudora', 3, None),
        ('5.1.05', 'Suministros y Materiales', 'Gasto', 'Deudora', 3, None),
        ('5.1.06', 'Gastos de Torneos y Eventos', 'Gasto', 'Deudora', 3, None),
        ('5.1.07', 'Depreciación', 'Gasto', 'Deudora', 3, None),
        ('5.1.08', 'Gastos Varios', 'Gasto', 'Deudora', 3, None),
    ]
    for cod, nom, tipo, nat, niv, padre in cuentas:
        c.execute('''INSERT OR IGNORE INTO plan_cuentas
            (codigo, nombre, tipo, naturaleza, nivel, cuenta_padre_id)
            VALUES (?, ?, ?, ?, ?, ?)''', (cod, nom, tipo, nat, niv, padre))
