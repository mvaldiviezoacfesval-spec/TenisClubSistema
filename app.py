from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file, session
from datetime import datetime, date, timedelta
from database import get_db, init_db
import io, os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'TenisClubMilagro2026_SecretKey')
APP_USERNAME = os.environ.get('APP_USERNAME', 'administraciontenisclub')
APP_PASSWORD = os.environ.get('APP_PASSWORD')

def create_app():
    init_db()
    return app

@app.context_processor
def inject_now():
    return {'now': datetime.now()}

@app.before_request
def proteger_sistema():
    rutas_publicas = {'login', 'health', 'static'}
    if request.endpoint in rutas_publicas:
        return None
    if session.get('autenticado'):
        return None
    return redirect(url_for('login', next=request.full_path if request.query_string else request.path))

@app.route('/login', methods=['GET','POST'])
def login():
    if session.get('autenticado'):
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        if not APP_PASSWORD:
            flash('La contrasena administrativa no esta configurada en el servidor.', 'danger')
            return render_template('login.html')
        usuario = request.form.get('usuario','').strip()
        contrasena = request.form.get('contrasena','')
        if usuario == APP_USERNAME and contrasena == APP_PASSWORD:
            session['autenticado'] = True
            session['usuario'] = usuario
            destino = request.args.get('next') or url_for('dashboard')
            if not destino.startswith('/') or destino.startswith('//'):
                destino = url_for('dashboard')
            session['welcome_next'] = destino
            return redirect(url_for('bienvenida'))
        flash('Usuario o contrasena incorrectos.', 'danger')
    return render_template('login.html')

@app.route('/bienvenida')
def bienvenida():
    destino = session.get('welcome_next') or url_for('dashboard')
    return render_template('bienvenida.html', destino=destino)

@app.route('/logout')
def logout():
    session.clear()
    flash('Sesion cerrada correctamente.', 'success')
    return redirect(url_for('login'))

@app.route('/proforma-oficial')
def proforma_oficial():
    return app.send_static_file('proforma_prf001.html')

@app.route('/health')
def health():
    return jsonify({'status': 'ok'})

# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────
def hoy():
    return date.today().isoformat()

def sig_numero(tabla, campo, prefijo, anio=None):
    conn = get_db()
    anio = anio or datetime.now().year
    patron = f"{prefijo}-{anio}-%"
    row = conn.execute(f"SELECT {campo} FROM {tabla} WHERE {campo} LIKE ? ORDER BY {campo} DESC LIMIT 1", (patron,)).fetchone()
    conn.close()
    if row:
        ultimo = int(row[0].split('-')[-1])
        return f"{prefijo}-{anio}-{ultimo+1:04d}"
    return f"{prefijo}-{anio}-0001"

def calcular_mora(vencimiento, monto, tasa=0.03):
    hoy_d = date.today()
    venc = date.fromisoformat(vencimiento)
    if hoy_d > venc:
        dias = (hoy_d - venc).days
        return round(monto * tasa * dias / 30, 3)
    return 0.0

# ─────────────────────────────────────────────
#  DASHBOARD  (Módulo 06)
# ─────────────────────────────────────────────
def sig_numero_conn(conn, tabla, campo, prefijo):
    anio = datetime.now().year
    patron = f"{prefijo}-{anio}-%"
    row = conn.execute(f"SELECT {campo} FROM {tabla} WHERE {campo} LIKE ? ORDER BY {campo} DESC LIMIT 1", (patron,)).fetchone()
    if row:
        ultimo = int(row[0].split('-')[-1])
        return f"{prefijo}-{anio}-{ultimo+1:04d}"
    return f"{prefijo}-{anio}-0001"

def cuenta_id(conn, codigo):
    cuenta = conn.execute("SELECT id FROM plan_cuentas WHERE codigo=? AND activa=1", (codigo,)).fetchone()
    if not cuenta:
        raise ValueError(f"No existe la cuenta contable activa {codigo}")
    return cuenta['id']

def crear_asiento_automatico(conn, fecha, concepto, referencia_tipo, referencia_id, detalles):
    detalles_validos = []
    total_debe = 0.0
    total_haber = 0.0
    for codigo, descripcion, debe, haber in detalles:
        debe = round(float(debe or 0), 3)
        haber = round(float(haber or 0), 3)
        if debe > 0 or haber > 0:
            detalles_validos.append((cuenta_id(conn, codigo), descripcion, debe, haber))
            total_debe += debe
            total_haber += haber

    if len(detalles_validos) < 2:
        return None
    if round(total_debe, 3) != round(total_haber, 3):
        raise ValueError(f"Asiento automatico descuadrado: debe {total_debe:.3f}, haber {total_haber:.3f}")

    numero = sig_numero_conn(conn, 'asientos', 'numero', 'ASI')
    cur = conn.execute('''INSERT INTO asientos
        (numero,fecha,concepto,tipo,referencia_tipo,referencia_id)
        VALUES(?,?,?,?,?,?)''', (
        numero, fecha, concepto, 'automatico', referencia_tipo, referencia_id
    ))
    asiento_id = cur.lastrowid
    for cuenta, descripcion, debe, haber in detalles_validos:
        conn.execute('''INSERT INTO asiento_detalles
            (asiento_id,cuenta_id,descripcion,debe,haber)
            VALUES(?,?,?,?,?)''', (asiento_id, cuenta, descripcion, debe, haber))
    return asiento_id

@app.route('/')
def dashboard():
    conn = get_db()
    mes = datetime.now().strftime('%Y-%m')
    anio = datetime.now().year

    total_socios = conn.execute("SELECT COUNT(*) FROM socios WHERE estado='Activo'").fetchone()[0]
    socios_mora = conn.execute("SELECT COUNT(DISTINCT socio_id) FROM cuotas WHERE estado='Pendiente' AND fecha_vencimiento < ?", (hoy(),)).fetchone()[0]

    ing_mes = conn.execute("SELECT COALESCE(SUM(total),0) FROM facturas_venta WHERE fecha LIKE ? AND estado!='Anulada'", (f"{mes}%",)).fetchone()[0]
    ing_cuotas = conn.execute("SELECT COALESCE(SUM(total),0) FROM cuotas WHERE fecha_pago LIKE ? AND estado='Pagada'", (f"{mes}%",)).fetchone()[0]
    total_ingresos = ing_mes + ing_cuotas

    eg_mes = conn.execute("SELECT COALESCE(SUM(total),0) FROM facturas_compra WHERE fecha LIKE ?", (f"{mes}%",)).fetchone()[0]

    cuotas_vencidas = conn.execute("SELECT COUNT(*) FROM cuotas WHERE estado='Pendiente' AND fecha_vencimiento < ?", (hoy(),)).fetchone()[0]
    cxc_total = conn.execute("SELECT COALESCE(SUM(saldo),0) FROM cuentas_cobrar WHERE estado='Pendiente'").fetchone()[0]
    cxp_total = conn.execute("SELECT COALESCE(SUM(saldo),0) FROM cuentas_pagar WHERE estado='Pendiente'").fetchone()[0]

    stock_critico = conn.execute("SELECT COUNT(*) FROM inventario WHERE stock_actual <= stock_minimo AND estado='Activo'").fetchone()[0]

    # Ingresos últimos 6 meses para gráfico
    meses_labels, meses_ingresos, meses_egresos = [], [], []
    for i in range(5, -1, -1):
        d = date.today().replace(day=1) - timedelta(days=i*28)
        m = d.strftime('%Y-%m')
        label = d.strftime('%b %Y')
        ing = conn.execute("SELECT COALESCE(SUM(total),0) FROM facturas_venta WHERE fecha LIKE ? AND estado!='Anulada'", (f"{m}%",)).fetchone()[0]
        ing += conn.execute("SELECT COALESCE(SUM(total),0) FROM cuotas WHERE fecha_pago LIKE ? AND estado='Pagada'", (f"{m}%",)).fetchone()[0]
        eg = conn.execute("SELECT COALESCE(SUM(total),0) FROM facturas_compra WHERE fecha LIKE ?", (f"{m}%",)).fetchone()[0]
        meses_labels.append(label); meses_ingresos.append(round(ing, 3)); meses_egresos.append(round(eg, 3))

    ultimas_facturas = conn.execute("SELECT * FROM facturas_venta ORDER BY created_at DESC LIMIT 5").fetchall()
    ultimas_cuotas = conn.execute("""
        SELECT c.*, s.nombres||' '||s.apellidos as socio_nombre
        FROM cuotas c JOIN socios s ON c.socio_id=s.id
        WHERE c.estado='Pendiente' ORDER BY c.fecha_vencimiento ASC LIMIT 5
    """).fetchall()
    conn.close()

    return render_template('dashboard.html',
        total_socios=total_socios, socios_mora=socios_mora,
        total_ingresos=total_ingresos, eg_mes=eg_mes,
        cuotas_vencidas=cuotas_vencidas, cxc_total=cxc_total,
        cxp_total=cxp_total, stock_critico=stock_critico,
        meses_labels=meses_labels, meses_ingresos=meses_ingresos,
        meses_egresos=meses_egresos,
        ultimas_facturas=ultimas_facturas, ultimas_cuotas=ultimas_cuotas
    )

# ─────────────────────────────────────────────
#  SOCIOS  (Módulo 05)
# ─────────────────────────────────────────────
@app.route('/socios')
def socios():
    q = request.args.get('q', '')
    estado = request.args.get('estado', '')
    conn = get_db()
    sql = "SELECT * FROM socios WHERE 1=1"
    params = []
    if q:
        sql += " AND (nombres LIKE ? OR apellidos LIKE ? OR cedula LIKE ? OR codigo LIKE ?)"
        params += [f'%{q}%']*4
    if estado:
        sql += " AND estado=?"
        params.append(estado)
    sql += " ORDER BY apellidos, nombres"
    socios_list = conn.execute(sql, params).fetchall()
    conn.close()
    return render_template('socios/index.html', socios=socios_list, q=q, estado=estado)

@app.route('/socios/nuevo', methods=['GET','POST'])
def socio_nuevo():
    if request.method == 'POST':
        conn = get_db()
        ultimo = conn.execute("SELECT codigo FROM socios ORDER BY id DESC LIMIT 1").fetchone()
        if ultimo:
            n = int(ultimo[0].replace('SOC-','')) + 1
        else:
            n = 1
        codigo = f"SOC-{n:04d}"
        try:
            conn.execute('''INSERT INTO socios
                (codigo,nombres,apellidos,cedula,email,telefono,direccion,
                 categoria,fecha_ingreso,fecha_nacimiento,cuota_mensual,observaciones)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?)''', (
                codigo,
                request.form['nombres'], request.form['apellidos'],
                request.form['cedula'], request.form.get('email',''),
                request.form.get('telefono',''), request.form.get('direccion',''),
                request.form.get('categoria','Activo'), request.form['fecha_ingreso'],
                request.form.get('fecha_nacimiento',''), float(request.form.get('cuota_mensual',30)),
                request.form.get('observaciones','')
            ))
            conn.commit()
            flash('Socio registrado correctamente.', 'success')
            return redirect(url_for('socios'))
        except Exception as e:
            flash(f'Error: {e}', 'danger')
        finally:
            conn.close()
    return render_template('socios/form.html', socio=None, accion='Nuevo')

@app.route('/socios/<int:id>/editar', methods=['GET','POST'])
def socio_editar(id):
    conn = get_db()
    socio = conn.execute("SELECT * FROM socios WHERE id=?", (id,)).fetchone()
    if request.method == 'POST':
        try:
            conn.execute('''UPDATE socios SET nombres=?,apellidos=?,cedula=?,email=?,
                telefono=?,direccion=?,categoria=?,fecha_ingreso=?,fecha_nacimiento=?,
                cuota_mensual=?,estado=?,observaciones=? WHERE id=?''', (
                request.form['nombres'], request.form['apellidos'],
                request.form['cedula'], request.form.get('email',''),
                request.form.get('telefono',''), request.form.get('direccion',''),
                request.form.get('categoria','Activo'), request.form['fecha_ingreso'],
                request.form.get('fecha_nacimiento',''), float(request.form.get('cuota_mensual',30)),
                request.form.get('estado','Activo'), request.form.get('observaciones',''), id
            ))
            conn.commit()
            flash('Socio actualizado.', 'success')
            return redirect(url_for('socios'))
        except Exception as e:
            flash(f'Error: {e}', 'danger')
    conn.close()
    return render_template('socios/form.html', socio=socio, accion='Editar')

@app.route('/socios/<int:id>')
def socio_detalle(id):
    conn = get_db()
    socio = conn.execute("SELECT * FROM socios WHERE id=?", (id,)).fetchone()
    cuotas = conn.execute("SELECT * FROM cuotas WHERE socio_id=? ORDER BY periodo DESC", (id,)).fetchall()
    conn.close()
    return render_template('socios/detalle.html', socio=socio, cuotas=cuotas)

# ─────────────────────────────────────────────
#  VENTAS  (Módulo 01)
# ─────────────────────────────────────────────
@app.route('/ventas')
def ventas():
    q = request.args.get('q','')
    conn = get_db()
    sql = "SELECT * FROM facturas_venta WHERE 1=1"
    params = []
    if q:
        sql += " AND (numero LIKE ? OR cliente_nombre LIKE ?)"
        params += [f'%{q}%']*2
    sql += " ORDER BY fecha DESC, id DESC"
    facturas = conn.execute(sql, params).fetchall()
    conn.close()
    return render_template('ventas/index.html', facturas=facturas, q=q)

@app.route('/ventas/nueva', methods=['GET','POST'])
def venta_nueva():
    if request.method == 'POST':
        conn = get_db()
        numero = sig_numero('facturas_venta', 'numero', 'FV')
        items_desc = request.form.getlist('item_desc[]')
        items_cant = request.form.getlist('item_cant[]')
        items_precio = request.form.getlist('item_precio[]')
        items_cuenta = request.form.getlist('item_cuenta_id[]')
        if len(items_cuenta) < len(items_desc):
            cuenta_default = str(cuenta_id(conn, '4.1.03'))
            items_cuenta += [cuenta_default] * (len(items_desc) - len(items_cuenta))
        subtotal = sum(float(c)*float(p) for c,p in zip(items_cant, items_precio))
        iva_pct = float(request.form.get('iva_pct', 15))
        iva = round(subtotal * iva_pct / 100, 3)
        total = round(subtotal + iva, 3)
        try:
            cur = conn.execute('''INSERT INTO facturas_venta
                (numero,fecha,cliente_nombre,subtotal,iva,total,estado,observaciones)
                VALUES(?,?,?,?,?,?,?,?)''', (
                numero, request.form['fecha'], request.form['cliente_nombre'],
                round(subtotal, 3), iva, total,
                request.form.get('estado','Emitida'), request.form.get('observaciones','')
            ))
            fid = cur.lastrowid
            ingresos_por_cuenta = {}
            for d,c,p,cuenta_ingreso_id in zip(items_desc, items_cant, items_precio, items_cuenta):
                if d.strip():
                    cuenta_ingreso_id = int(cuenta_ingreso_id or cuenta_id(conn, '4.1.03'))
                    sub_item = round(float(c)*float(p), 3)
                    conn.execute('''INSERT INTO factura_venta_items
                        (factura_id,descripcion,cantidad,precio_unitario,subtotal,cuenta_ingreso_id)
                        VALUES(?,?,?,?,?,?)''', (fid, d, float(c), float(p), sub_item, cuenta_ingreso_id))
                    ingresos_por_cuenta[cuenta_ingreso_id] = ingresos_por_cuenta.get(cuenta_ingreso_id, 0) + sub_item
            if request.form.get('estado','Emitida') != 'Anulada':
                conn.execute('''INSERT INTO cuentas_cobrar
                    (numero,fecha_emision,fecha_vencimiento,cliente_nombre,concepto,
                     monto_original,monto_pagado,saldo,estado,referencia,referencia_tipo,referencia_id)
                    VALUES(?,?,?,?,?,?,0,?,?,?,?,?)''', (
                    sig_numero('cuentas_cobrar','numero','CXC'),
                    request.form['fecha'], request.form['fecha'],
                    request.form['cliente_nombre'], f"Factura de venta {numero}",
                    total, total, 'Pendiente', numero, 'factura_venta', fid
                ))
                detalles_asiento = [('1.1.04', f"CxC factura {numero}", total, 0)]
                for cuenta_ingreso_id, monto in ingresos_por_cuenta.items():
                    cuenta = conn.execute("SELECT codigo, nombre FROM plan_cuentas WHERE id=?", (cuenta_ingreso_id,)).fetchone()
                    if cuenta:
                        detalles_asiento.append((cuenta['codigo'], f"{cuenta['nombre']} factura {numero}", 0, round(monto, 3)))
                detalles_asiento.append(('2.1.02', f"IVA factura {numero}", 0, iva))
                crear_asiento_automatico(conn, request.form['fecha'], f"Venta {numero} - {request.form['cliente_nombre']}",
                    'factura_venta', fid, detalles_asiento)
            conn.commit()
            flash(f'Factura {numero} registrada y cargada automaticamente en Cuentas por Cobrar.', 'success')
            return redirect(url_for('ventas'))
        except Exception as e:
            flash(f'Error: {e}', 'danger')
        finally:
            conn.close()
    numero_preview = sig_numero('facturas_venta', 'numero', 'FV')
    conn = get_db()
    cuentas_ingreso = conn.execute("SELECT * FROM plan_cuentas WHERE activa=1 AND tipo='Ingreso' AND nivel>=3 ORDER BY codigo").fetchall()
    conn.close()
    return render_template('ventas/form.html', numero=numero_preview, hoy=hoy(), cuentas_ingreso=cuentas_ingreso)

@app.route('/ventas/<int:id>')
def venta_detalle(id):
    conn = get_db()
    factura = conn.execute("SELECT * FROM facturas_venta WHERE id=?", (id,)).fetchone()
    items = conn.execute('''
        SELECT i.*, p.codigo as cuenta_codigo, p.nombre as cuenta_nombre
        FROM factura_venta_items i
        LEFT JOIN plan_cuentas p ON p.id=i.cuenta_ingreso_id
        WHERE i.factura_id=?
    ''', (id,)).fetchall()
    conn.close()
    return render_template('ventas/detalle.html', factura=factura, items=items)

@app.route('/ventas/<int:id>/anular', methods=['POST'])
def venta_anular(id):
    conn = get_db()
    factura = conn.execute("SELECT * FROM facturas_venta WHERE id=?", (id,)).fetchone()
    if not factura or factura['estado'] == 'Anulada':
        conn.close()
        flash('La factura ya se encuentra anulada o no existe.', 'warning')
        return redirect(url_for('ventas'))
    cxc = conn.execute("SELECT * FROM cuentas_cobrar WHERE referencia_tipo='factura_venta' AND referencia_id=?", (id,)).fetchone()
    if cxc and (cxc['monto_pagado'] or 0) > 0:
        conn.close()
        flash('No se puede anular una factura con abonos en Cuentas por Cobrar. Primero reversa los cobros relacionados.', 'danger')
        return redirect(url_for('ventas'))
    conn.execute("UPDATE facturas_venta SET estado='Anulada' WHERE id=?", (id,))
    conn.execute('''UPDATE cuentas_cobrar
        SET estado='Anulada', monto_pagado=0, saldo=0
        WHERE referencia_tipo='factura_venta' AND referencia_id=? AND estado!='Pagada' ''', (id,))
    if factura:
        crear_asiento_automatico(conn, hoy(), f"Anulacion venta {factura['numero']}",
            'anulacion_factura_venta', id, [
            ('4.1.03', f"Reverso ingreso {factura['numero']}", factura['subtotal'], 0),
            ('2.1.02', f"Reverso IVA {factura['numero']}", factura['iva'], 0),
            ('1.1.04', f"Reverso CxC {factura['numero']}", 0, factura['total']),
        ])
    conn.commit(); conn.close()
    flash('Factura anulada y Cuenta por Cobrar vinculada revertida.', 'warning')
    return redirect(url_for('ventas'))

# ─────────────────────────────────────────────
#  COMPRAS  (Módulo 01)
# ─────────────────────────────────────────────
@app.route('/compras')
def compras():
    conn = get_db()
    facturas = conn.execute("SELECT * FROM facturas_compra ORDER BY fecha DESC").fetchall()
    conn.close()
    return render_template('compras/index.html', facturas=facturas)

@app.route('/compras/nueva', methods=['GET','POST'])
def compra_nueva():
    if request.method == 'POST':
        conn = get_db()
        items_desc = request.form.getlist('item_desc[]')
        items_cant = request.form.getlist('item_cant[]')
        items_precio = request.form.getlist('item_precio[]')
        subtotal = sum(float(c)*float(p) for c,p in zip(items_cant, items_precio))
        iva_pct = float(request.form.get('iva_pct', 15))
        iva = round(subtotal * iva_pct / 100, 3)
        total = round(subtotal + iva, 3)
        try:
            cur = conn.execute('''INSERT INTO facturas_compra
                (numero,fecha,proveedor_nombre,subtotal,iva,total,estado,observaciones)
                VALUES(?,?,?,?,?,?,?,?)''', (
                request.form['numero'], request.form['fecha'],
                request.form['proveedor_nombre'], round(subtotal, 3), iva, total,
                'Registrada', request.form.get('observaciones','')
            ))
            fid = cur.lastrowid
            for d,c,p in zip(items_desc, items_cant, items_precio):
                if d.strip():
                    conn.execute('''INSERT INTO factura_compra_items
                        (factura_id,descripcion,cantidad,precio_unitario,subtotal)
                        VALUES(?,?,?,?,?)''', (fid, d, float(c), float(p), float(c)*float(p)))
            fecha_vencimiento = request.form.get('fecha_vencimiento') or request.form['fecha']
            conn.execute('''INSERT INTO cuentas_pagar
                (numero,fecha_emision,fecha_vencimiento,proveedor_nombre,concepto,
                 monto_original,monto_pagado,saldo,estado,referencia,referencia_tipo,referencia_id)
                VALUES(?,?,?,?,?,?,0,?,?,?,?,?)''', (
                sig_numero('cuentas_pagar','numero','CXP'),
                request.form['fecha'], fecha_vencimiento,
                request.form['proveedor_nombre'],
                f"Factura de compra {request.form['numero']}",
                total, total, 'Pendiente',
                request.form['numero'], 'factura_compra', fid
            ))
            crear_asiento_automatico(conn, request.form['fecha'], f"Compra {request.form['numero']} - {request.form['proveedor_nombre']}",
                'factura_compra', fid, [
                ('5.1.08', f"Gasto compra {request.form['numero']}", round(subtotal, 3), 0),
                ('1.1.07', f"IVA compra {request.form['numero']}", iva, 0),
                ('2.1.01', f"CxP compra {request.form['numero']}", 0, total),
            ])
            conn.commit()
            flash('Factura de compra registrada y cargada automaticamente en cuentas por pagar.', 'success')
            return redirect(url_for('compras'))
        except Exception as e:
            flash(f'Error: {e}', 'danger')
        finally:
            conn.close()
    return render_template('compras/form.html', hoy=hoy())

# ─────────────────────────────────────────────
#  NOTAS DE CRÉDITO
# ─────────────────────────────────────────────
@app.route('/notas-credito')
def notas_credito():
    conn = get_db()
    notas = conn.execute("SELECT * FROM notas_credito ORDER BY fecha DESC").fetchall()
    conn.close()
    return render_template('notas_credito/index.html', notas=notas)

@app.route('/notas-credito/nueva', methods=['GET','POST'])
def nota_credito_nueva():
    if request.method == 'POST':
        conn = get_db()
        numero = sig_numero('notas_credito', 'numero', 'NC')
        try:
            conn.execute('''INSERT INTO notas_credito
                (numero,fecha,factura_ref,cliente_nombre,motivo,total,tipo)
                VALUES(?,?,?,?,?,?,?)''', (
                numero, request.form['fecha'], request.form.get('factura_ref',''),
                request.form['cliente_nombre'], request.form['motivo'],
                float(request.form['total']), request.form.get('tipo','Venta')
            ))
            conn.commit()
            flash(f'Nota de crédito {numero} emitida.', 'success')
            return redirect(url_for('notas_credito'))
        except Exception as e:
            flash(f'Error: {e}', 'danger')
        finally:
            conn.close()
    numero_preview = sig_numero('notas_credito', 'numero', 'NC')
    return render_template('notas_credito/form.html', numero=numero_preview, hoy=hoy())

# ─────────────────────────────────────────────
#  CUOTAS DE SOCIOS  (Módulo 07)
# ─────────────────────────────────────────────
@app.route('/cuotas')
def cuotas():
    estado = request.args.get('estado','')
    mes = request.args.get('mes','')
    conn = get_db()
    sql = """SELECT c.*, s.nombres||' '||s.apellidos as socio_nombre, s.codigo as socio_codigo
             FROM cuotas c JOIN socios s ON c.socio_id=s.id WHERE 1=1"""
    params = []
    if estado:
        sql += " AND c.estado=?"; params.append(estado)
    if mes:
        sql += " AND c.periodo=?"; params.append(mes)
    sql += " ORDER BY c.fecha_vencimiento ASC"
    cuotas_list = conn.execute(sql, params).fetchall()
    conn.close()
    return render_template('cuotas/index.html', cuotas=cuotas_list, estado=estado, mes=mes)

@app.route('/cuotas/generar', methods=['GET','POST'])
def cuotas_generar():
    if request.method == 'POST':
        periodo = request.form['periodo']
        conn = get_db()
        socios_activos = conn.execute("SELECT * FROM socios WHERE estado='Activo'").fetchall()
        anio, mes_n = map(int, periodo.split('-'))
        ultimo_dia = (date(anio, mes_n % 12 + 1, 1) - timedelta(days=1)) if mes_n < 12 else date(anio, 12, 31)
        generadas = 0
        for s in socios_activos:
            existe = conn.execute("SELECT id FROM cuotas WHERE socio_id=? AND periodo=?", (s['id'], periodo)).fetchone()
            if not existe:
                conn.execute('''INSERT INTO cuotas
                    (socio_id,periodo,fecha_vencimiento,monto,mora,total,estado)
                    VALUES(?,?,?,?,0,?,?)''', (
                    s['id'], periodo, ultimo_dia.isoformat(),
                    s['cuota_mensual'], s['cuota_mensual'], 'Pendiente'
                ))
                generadas += 1
        conn.commit(); conn.close()
        flash(f'Se generaron {generadas} cuotas para {periodo}.', 'success')
        return redirect(url_for('cuotas', mes=periodo))
    return render_template('cuotas/generar.html', hoy=hoy())

@app.route('/cuotas/<int:id>/pagar', methods=['POST'])
def cuota_pagar(id):
    conn = get_db()
    cuota = conn.execute("SELECT * FROM cuotas WHERE id=?", (id,)).fetchone()
    mora = calcular_mora(cuota['fecha_vencimiento'], cuota['monto'])
    total = cuota['monto'] + mora
    conn.execute('''UPDATE cuotas SET estado='Pagada', fecha_pago=?, metodo_pago=?,
        mora=?, total=?, comprobante=? WHERE id=?''', (
        hoy(), request.form.get('metodo','Efectivo'), mora, total,
        request.form.get('comprobante',''), id
    ))
    conn.commit(); conn.close()
    flash('Pago registrado correctamente.', 'success')
    return redirect(url_for('cuotas'))

# ─────────────────────────────────────────────
#  CUENTAS POR COBRAR / PAGAR  (Módulo 08)
# ─────────────────────────────────────────────
@app.route('/cxc')
def cxc():
    conn = get_db()
    cuentas = conn.execute("SELECT * FROM cuentas_cobrar ORDER BY fecha_vencimiento ASC").fetchall()
    total_pend = conn.execute("SELECT COALESCE(SUM(saldo),0) FROM cuentas_cobrar WHERE estado='Pendiente'").fetchone()[0]
    vencidas = conn.execute("SELECT COALESCE(SUM(saldo),0) FROM cuentas_cobrar WHERE estado='Pendiente' AND fecha_vencimiento < ?", (hoy(),)).fetchone()[0]
    conn.close()
    return render_template('cxc/index.html', cuentas=cuentas, total_pend=total_pend, vencidas=vencidas, hoy=hoy())

@app.route('/cxc/nueva', methods=['GET','POST'])
def cxc_nueva():
    if request.method == 'POST':
        conn = get_db()
        monto = float(request.form['monto_original'])
        try:
            conn.execute('''INSERT INTO cuentas_cobrar
                (numero,fecha_emision,fecha_vencimiento,cliente_nombre,concepto,
                 monto_original,monto_pagado,saldo,referencia)
                VALUES(?,?,?,?,?,?,0,?,?)''', (
                sig_numero('cuentas_cobrar','numero','CXC'),
                request.form['fecha_emision'], request.form['fecha_vencimiento'],
                request.form['cliente_nombre'], request.form['concepto'],
                monto, monto, request.form.get('referencia','')
            ))
            conn.commit()
            flash('Cuenta por cobrar registrada.', 'success')
            return redirect(url_for('cxc'))
        except Exception as e:
            flash(f'Error: {e}', 'danger')
        finally:
            conn.close()
    return render_template('cxc/form.html', hoy=hoy())

@app.route('/cxc/<int:id>/abonar', methods=['POST'])
def cxc_abonar(id):
    conn = get_db()
    cuenta = conn.execute("SELECT * FROM cuentas_cobrar WHERE id=?", (id,)).fetchone()
    abono = float(request.form['abono'])
    nuevo_pagado = cuenta['monto_pagado'] + abono
    nuevo_saldo = cuenta['monto_original'] - nuevo_pagado
    estado = 'Pagada' if nuevo_saldo <= 0 else 'Parcial'
    conn.execute("UPDATE cuentas_cobrar SET monto_pagado=?, saldo=?, estado=? WHERE id=?",
                 (round(nuevo_pagado, 3), round(max(nuevo_saldo,0), 3), estado, id))
    crear_asiento_automatico(conn, request.form.get('fecha_cobro') or hoy(), f"Cobro CxC {cuenta['numero']} - {cuenta['cliente_nombre']}",
        'cobro_cxc', id, [
        ('1.1.02', f"Cobro {cuenta['numero']}", abono, 0),
        ('1.1.04', f"Abono CxC {cuenta['numero']}", 0, abono),
    ])
    conn.commit(); conn.close()
    flash('Abono registrado.', 'success')
    return redirect(url_for('cxc'))

@app.route('/cxp')
def cxp():
    estado = request.args.get('estado','')
    mes = request.args.get('mes','')
    conn = get_db()
    sql = "SELECT * FROM cuentas_pagar WHERE 1=1"
    params = []
    if estado:
        sql += " AND estado=?"; params.append(estado)
    if mes:
        sql += " AND fecha_vencimiento LIKE ?"; params.append(f"{mes}%")
    sql += " ORDER BY fecha_vencimiento ASC"
    cuentas = conn.execute(sql, params).fetchall()
    total_pend = conn.execute("SELECT COALESCE(SUM(saldo),0) FROM cuentas_pagar WHERE estado!='Pagada'").fetchone()[0]
    vencidas = conn.execute("SELECT COALESCE(SUM(saldo),0) FROM cuentas_pagar WHERE estado!='Pagada' AND fecha_vencimiento < ?", (hoy(),)).fetchone()[0]
    conn.close()
    return render_template('cxp/index.html', cuentas=cuentas, total_pend=total_pend, vencidas=vencidas, hoy=hoy(), estado=estado, mes=mes)

@app.route('/cxp/nueva', methods=['GET','POST'])
def cxp_nueva():
    if request.method == 'POST':
        conn = get_db()
        monto = float(request.form['monto_original'])
        try:
            conn.execute('''INSERT INTO cuentas_pagar
                (numero,fecha_emision,fecha_vencimiento,proveedor_nombre,concepto,
                 monto_original,monto_pagado,saldo,referencia)
                VALUES(?,?,?,?,?,?,0,?,?)''', (
                sig_numero('cuentas_pagar','numero','CXP'),
                request.form['fecha_emision'], request.form['fecha_vencimiento'],
                request.form['proveedor_nombre'], request.form['concepto'],
                monto, monto, request.form.get('referencia','')
            ))
            conn.commit()
            flash('Cuenta por pagar registrada.', 'success')
            return redirect(url_for('cxp'))
        except Exception as e:
            flash(f'Error: {e}', 'danger')
        finally:
            conn.close()
    return render_template('cxp/form.html', hoy=hoy())

@app.route('/cxp/<int:id>/pagar', methods=['POST'])
def cxp_pagar(id):
    conn = get_db()
    cuenta = conn.execute("SELECT * FROM cuentas_pagar WHERE id=?", (id,)).fetchone()
    pago = float(request.form['pago'])
    nuevo_pagado = cuenta['monto_pagado'] + pago
    nuevo_saldo = cuenta['monto_original'] - nuevo_pagado
    estado = 'Pagada' if nuevo_saldo <= 0 else 'Parcial'
    conn.execute("UPDATE cuentas_pagar SET monto_pagado=?, saldo=?, estado=? WHERE id=?",
                 (round(nuevo_pagado, 3), round(max(nuevo_saldo,0), 3), estado, id))
    asiento_id = crear_asiento_automatico(conn, request.form.get('fecha_pago') or hoy(), f"Pago CxP {cuenta['numero']} - {cuenta['proveedor_nombre']}",
        'pago_cxp', id, [
        ('2.1.01', f"Pago {cuenta['numero']}", pago, 0),
        ('1.1.02', f"Salida banco {cuenta['numero']}", 0, pago),
    ])
    conn.execute('''INSERT INTO movimientos_bancarios
        (cuenta_bancaria,fecha,descripcion,tipo,monto,saldo_banco,referencia,conciliado,asiento_id)
        VALUES(?,?,?,?,?,?,?,0,?)''', (
        request.form.get('cuenta_bancaria') or 'Banco principal',
        request.form.get('fecha_pago') or hoy(),
        f"Pago CxP {cuenta['numero']} - {cuenta['proveedor_nombre']}",
        'Egreso', pago, None, cuenta['numero'], asiento_id
    ))
    conn.commit(); conn.close()
    flash('Pago registrado y enviado a conciliacion bancaria como egreso.', 'success')
    return redirect(url_for('cxp'))

# ─────────────────────────────────────────────
#  CONCILIACIÓN BANCARIA  (Módulo 09)
# ─────────────────────────────────────────────
@app.route('/revision-documentos')
def revision_documentos():
    tipo = request.args.get('tipo', 'cxc')
    conn = get_db()
    pagos_cxp = conn.execute('''
        SELECT m.*, c.id as cuenta_id, c.proveedor_nombre, c.concepto,
               c.monto_original, c.monto_pagado, c.saldo, c.estado as cuenta_estado
        FROM movimientos_bancarios m
        LEFT JOIN cuentas_pagar c ON c.numero = m.referencia
        WHERE m.tipo='Egreso'
          AND m.descripcion LIKE 'Pago CxP %'
        ORDER BY m.fecha DESC, m.id DESC
    ''').fetchall()
    cuentas_cobrar = conn.execute('''
        SELECT c.*, f.numero as factura_numero, f.estado as factura_estado
        FROM cuentas_cobrar c
        LEFT JOIN facturas_venta f ON c.referencia_tipo='factura_venta' AND c.referencia_id=f.id
        WHERE c.estado!='Anulada'
        ORDER BY c.fecha_emision DESC, c.id DESC
    ''').fetchall()
    facturas_venta = conn.execute('''
        SELECT f.*, c.numero as cxc_numero, c.estado as cxc_estado, c.saldo as cxc_saldo
        FROM facturas_venta f
        LEFT JOIN cuentas_cobrar c ON c.referencia_tipo='factura_venta' AND c.referencia_id=f.id
        WHERE f.estado!='Anulada'
        ORDER BY f.fecha DESC, f.id DESC
    ''').fetchall()
    facturas_compra = conn.execute('''
        SELECT f.*, c.id as cxp_id, c.numero as cxp_numero, c.estado as cxp_estado,
               c.monto_pagado as cxp_pagado, c.saldo as cxp_saldo
        FROM facturas_compra f
        LEFT JOIN cuentas_pagar c ON c.referencia_tipo='factura_compra' AND c.referencia_id=f.id
        WHERE f.estado!='Anulada'
        ORDER BY f.fecha DESC, f.id DESC
    ''').fetchall()
    conn.close()
    return render_template('revision_documentos/index.html', tipo=tipo, pagos_cxp=pagos_cxp,
                           cuentas_cobrar=cuentas_cobrar, facturas_venta=facturas_venta,
                           facturas_compra=facturas_compra)

@app.route('/revision-documentos/cxc/<int:cuenta_id>/anular', methods=['POST'])
def revision_anular_cxc(cuenta_id):
    conn = get_db()
    cuenta = conn.execute("SELECT * FROM cuentas_cobrar WHERE id=?", (cuenta_id,)).fetchone()
    if not cuenta or cuenta['estado'] == 'Anulada':
        conn.close()
        flash('La Cuenta por Cobrar ya esta anulada o no existe.', 'warning')
        return redirect(url_for('revision_documentos', tipo='cxc'))
    if (cuenta['monto_pagado'] or 0) > 0:
        conn.close()
        flash('No se puede anular una CxC con abonos registrados. Primero revisa y reversa los cobros relacionados.', 'danger')
        return redirect(url_for('revision_documentos', tipo='cxc'))

    if cuenta['referencia_tipo'] == 'factura_venta' and cuenta['referencia_id']:
        factura = conn.execute("SELECT * FROM facturas_venta WHERE id=?", (cuenta['referencia_id'],)).fetchone()
        if factura and factura['estado'] != 'Anulada':
            conn.execute("UPDATE facturas_venta SET estado='Anulada' WHERE id=?", (factura['id'],))
            crear_asiento_automatico(conn, hoy(), f"Anulacion CxC factura {factura['numero']}",
                'anulacion_cxc', cuenta_id, [
                ('4.1.03', f"Reverso ingreso {factura['numero']}", factura['subtotal'], 0),
                ('2.1.02', f"Reverso IVA {factura['numero']}", factura['iva'], 0),
                ('1.1.04', f"Reverso CxC {factura['numero']}", 0, factura['total']),
            ])

    conn.execute("UPDATE cuentas_cobrar SET estado='Anulada', monto_pagado=0, saldo=0 WHERE id=?", (cuenta_id,))
    conn.commit()
    conn.close()
    flash('Cuenta por Cobrar anulada correctamente.', 'success')
    return redirect(url_for('revision_documentos', tipo='cxc'))

@app.route('/revision-documentos/factura-venta/<int:factura_id>/anular', methods=['POST'])
def revision_anular_factura_venta(factura_id):
    conn = get_db()
    factura = conn.execute("SELECT * FROM facturas_venta WHERE id=?", (factura_id,)).fetchone()
    if not factura or factura['estado'] == 'Anulada':
        conn.close()
        flash('La factura ya se encuentra anulada o no existe.', 'warning')
        return redirect(url_for('revision_documentos', tipo='ventas'))
    cxc = conn.execute("SELECT * FROM cuentas_cobrar WHERE referencia_tipo='factura_venta' AND referencia_id=?", (factura_id,)).fetchone()
    if cxc and (cxc['monto_pagado'] or 0) > 0:
        conn.close()
        flash('No se puede anular una factura con abonos en Cuentas por Cobrar. Primero reversa los cobros relacionados.', 'danger')
        return redirect(url_for('revision_documentos', tipo='ventas'))

    conn.execute("UPDATE facturas_venta SET estado='Anulada' WHERE id=?", (factura_id,))
    conn.execute('''UPDATE cuentas_cobrar
        SET estado='Anulada', monto_pagado=0, saldo=0
        WHERE referencia_tipo='factura_venta' AND referencia_id=? AND estado!='Pagada' ''', (factura_id,))
    crear_asiento_automatico(conn, hoy(), f"Anulacion venta {factura['numero']}",
        'anulacion_factura_venta', factura_id, [
        ('4.1.03', f"Reverso ingreso {factura['numero']}", factura['subtotal'], 0),
        ('2.1.02', f"Reverso IVA {factura['numero']}", factura['iva'], 0),
        ('1.1.04', f"Reverso CxC {factura['numero']}", 0, factura['total']),
    ])
    conn.commit()
    conn.close()
    flash('Factura de venta anulada y asiento reversado correctamente.', 'success')
    return redirect(url_for('revision_documentos', tipo='ventas'))

@app.route('/revision-documentos/compra/<int:factura_id>/anular', methods=['POST'])
def revision_anular_compra(factura_id):
    conn = get_db()
    factura = conn.execute("SELECT * FROM facturas_compra WHERE id=?", (factura_id,)).fetchone()
    if not factura or factura['estado'] == 'Anulada':
        conn.close()
        flash('La compra ya esta anulada o no existe.', 'warning')
        return redirect(url_for('revision_documentos', tipo='compras'))
    cxp = conn.execute("SELECT * FROM cuentas_pagar WHERE referencia_tipo='factura_compra' AND referencia_id=?", (factura_id,)).fetchone()
    if cxp and (cxp['monto_pagado'] or 0) > 0:
        conn.close()
        flash('No se puede anular una compra con pagos registrados. Primero anula el pago desde Pagos CxP.', 'danger')
        return redirect(url_for('revision_documentos', tipo='compras'))

    conn.execute("UPDATE facturas_compra SET estado='Anulada' WHERE id=?", (factura_id,))
    if cxp:
        conn.execute("UPDATE cuentas_pagar SET estado='Anulada', monto_pagado=0, saldo=0 WHERE id=?", (cxp['id'],))
    crear_asiento_automatico(conn, hoy(), f"Anulacion compra {factura['numero']}",
        'anulacion_factura_compra', factura_id, [
        ('2.1.01', f"Reverso CxP compra {factura['numero']}", factura['total'], 0),
        ('5.1.08', f"Reverso gasto compra {factura['numero']}", 0, factura['subtotal']),
        ('1.1.07', f"Reverso IVA compra {factura['numero']}", 0, factura['iva']),
    ])
    conn.commit()
    conn.close()
    flash('Compra anulada y asiento reversado correctamente.', 'success')
    return redirect(url_for('revision_documentos', tipo='compras'))

@app.route('/revision-documentos/pago-cxp/<int:movimiento_id>/anular', methods=['POST'])
def revision_anular_pago_cxp(movimiento_id):
    conn = get_db()
    movimiento = conn.execute('''
        SELECT m.*, c.id as cuenta_id, c.monto_original, c.monto_pagado
        FROM movimientos_bancarios m
        JOIN cuentas_pagar c ON c.numero = m.referencia
        WHERE m.id=? AND m.tipo='Egreso' AND m.descripcion LIKE 'Pago CxP %'
    ''', (movimiento_id,)).fetchone()
    if not movimiento:
        conn.close()
        flash('No se encontro un pago CxP valido para anular.', 'danger')
        return redirect(url_for('revision_documentos'))

    nuevo_pagado = max((movimiento['monto_pagado'] or 0) - movimiento['monto'], 0)
    nuevo_saldo = max((movimiento['monto_original'] or 0) - nuevo_pagado, 0)
    if nuevo_pagado <= 0:
        estado = 'Pendiente'
    elif nuevo_saldo <= 0:
        estado = 'Pagada'
    else:
        estado = 'Parcial'

    conn.execute("UPDATE cuentas_pagar SET monto_pagado=?, saldo=?, estado=? WHERE id=?",
                 (round(nuevo_pagado, 3), round(nuevo_saldo, 3), estado, movimiento['cuenta_id']))
    crear_asiento_automatico(conn, hoy(), f"Anulacion pago CxP {movimiento['referencia']}",
        'anulacion_pago_cxp', movimiento_id, [
        ('1.1.02', f"Reverso banco {movimiento['referencia']}", movimiento['monto'], 0),
        ('2.1.01', f"Reverso pago {movimiento['referencia']}", 0, movimiento['monto']),
    ])
    conn.execute("DELETE FROM movimientos_bancarios WHERE id=?", (movimiento_id,))
    conn.commit()
    conn.close()
    flash('Pago anulado: se elimino el egreso bancario y se devolvio el saldo a Cuentas por Pagar.', 'success')
    return redirect(url_for('revision_documentos'))

@app.route('/bancaria')
def bancaria():
    mes = request.args.get('mes') or datetime.now().strftime('%Y-%m')
    conn = get_db()
    movimientos = conn.execute("SELECT * FROM movimientos_bancarios WHERE fecha LIKE ? ORDER BY fecha DESC", (f"{mes}%",)).fetchall()
    pendientes = conn.execute("SELECT COUNT(*) FROM movimientos_bancarios WHERE conciliado=0 AND fecha LIKE ?", (f"{mes}%",)).fetchone()[0]
    ingresos = conn.execute("SELECT COALESCE(SUM(monto),0) FROM movimientos_bancarios WHERE tipo='Ingreso' AND fecha LIKE ?", (f"{mes}%",)).fetchone()[0]
    egresos = conn.execute("SELECT COALESCE(SUM(monto),0) FROM movimientos_bancarios WHERE tipo='Egreso' AND fecha LIKE ?", (f"{mes}%",)).fetchone()[0]
    conciliados = conn.execute("SELECT COUNT(*) FROM movimientos_bancarios WHERE conciliado=1 AND fecha LIKE ?", (f"{mes}%",)).fetchone()[0]
    conn.close()
    return render_template('bancaria/index.html', movimientos=movimientos, pendientes=pendientes,
                           ingresos=ingresos, egresos=egresos, conciliados=conciliados, mes=mes)

@app.route('/bancaria/nuevo', methods=['GET','POST'])
def bancaria_nuevo():
    if request.method == 'POST':
        conn = get_db()
        try:
            conn.execute('''INSERT INTO movimientos_bancarios
                (cuenta_bancaria,fecha,descripcion,tipo,monto,saldo_banco,referencia)
                VALUES(?,?,?,?,?,?,?)''', (
                request.form['cuenta_bancaria'], request.form['fecha'],
                request.form['descripcion'], request.form['tipo'],
                float(request.form['monto']), float(request.form.get('saldo_banco',0) or 0),
                request.form.get('referencia','')
            ))
            conn.commit()
            flash('Movimiento bancario registrado.', 'success')
            return redirect(url_for('bancaria', mes=request.form['fecha'][:7]))
        except Exception as e:
            flash(f'Error: {e}', 'danger')
        finally:
            conn.close()
    return render_template('bancaria/form.html', hoy=hoy())

@app.route('/bancaria/<int:id>/conciliar', methods=['POST'])
def bancaria_conciliar(id):
    conn = get_db()
    conn.execute("UPDATE movimientos_bancarios SET conciliado=1 WHERE id=?", (id,))
    conn.commit(); conn.close()
    flash('Movimiento conciliado.', 'success')
    return redirect(url_for('bancaria', mes=request.form.get('mes') or datetime.now().strftime('%Y-%m')))

# ─────────────────────────────────────────────
#  INVENTARIO  (Módulo 10)
# ─────────────────────────────────────────────
@app.route('/bancaria/<int:id>/desconciliar', methods=['POST'])
def bancaria_desconciliar(id):
    conn = get_db()
    conn.execute("UPDATE movimientos_bancarios SET conciliado=0 WHERE id=?", (id,))
    conn.commit(); conn.close()
    flash('Conciliacion quitada. El movimiento vuelve a pendientes.', 'warning')
    return redirect(url_for('bancaria', mes=request.form.get('mes') or datetime.now().strftime('%Y-%m')))

@app.route('/bancaria/<int:id>/eliminar', methods=['POST'])
def bancaria_eliminar(id):
    conn = get_db()
    conn.execute("DELETE FROM movimientos_bancarios WHERE id=?", (id,))
    conn.commit(); conn.close()
    flash('Movimiento bancario eliminado.', 'warning')
    return redirect(url_for('bancaria', mes=request.form.get('mes') or datetime.now().strftime('%Y-%m')))

@app.route('/inventario')
def inventario():
    conn = get_db()
    productos = conn.execute("SELECT * FROM inventario ORDER BY nombre").fetchall()
    conn.close()
    return render_template('inventario/index.html', productos=productos)

@app.route('/inventario/nuevo', methods=['GET','POST'])
def inventario_nuevo():
    if request.method == 'POST':
        conn = get_db()
        try:
            conn.execute('''INSERT INTO inventario
                (codigo,nombre,descripcion,categoria,unidad,stock_actual,stock_minimo,
                 precio_costo,precio_venta,ubicacion)
                VALUES(?,?,?,?,?,?,?,?,?,?)''', (
                request.form['codigo'], request.form['nombre'],
                request.form.get('descripcion',''), request.form.get('categoria',''),
                request.form.get('unidad','Unidad'),
                float(request.form.get('stock_actual',0)),
                float(request.form.get('stock_minimo',5)),
                float(request.form.get('precio_costo',0)),
                float(request.form.get('precio_venta',0)),
                request.form.get('ubicacion','')
            ))
            conn.commit()
            flash('Producto registrado.', 'success')
            return redirect(url_for('inventario'))
        except Exception as e:
            flash(f'Error: {e}', 'danger')
        finally:
            conn.close()
    return render_template('inventario/form.html', producto=None)

@app.route('/inventario/<int:id>/movimiento', methods=['POST'])
def inventario_movimiento(id):
    conn = get_db()
    prod = conn.execute("SELECT * FROM inventario WHERE id=?", (id,)).fetchone()
    tipo = request.form['tipo']
    cant = float(request.form['cantidad'])
    nuevo_stock = prod['stock_actual'] + cant if tipo == 'Entrada' else prod['stock_actual'] - cant
    if nuevo_stock < 0:
        flash('Stock insuficiente.', 'danger')
    else:
        conn.execute("UPDATE inventario SET stock_actual=? WHERE id=?", (nuevo_stock, id))
        conn.execute('''INSERT INTO movimientos_inventario
            (producto_id,fecha,tipo,cantidad,precio_unitario,referencia,stock_resultante)
            VALUES(?,?,?,?,?,?,?)''', (
            id, hoy(), tipo, cant,
            float(request.form.get('precio_unitario',0)),
            request.form.get('referencia',''), nuevo_stock
        ))
        conn.commit()
        flash('Movimiento registrado.', 'success')
    conn.close()
    return redirect(url_for('inventario'))

# ─────────────────────────────────────────────
#  NÓMINA  (Módulo 11)
# ─────────────────────────────────────────────
@app.route('/nomina')
def nomina():
    conn = get_db()
    empleados = conn.execute("SELECT * FROM empleados WHERE estado='Activo' ORDER BY apellidos").fetchall()
    roles = conn.execute("""
        SELECT r.*, e.nombres||' '||e.apellidos as emp_nombre
        FROM roles_pago r JOIN empleados e ON r.empleado_id=e.id
        ORDER BY r.periodo DESC, e.apellidos
    """).fetchall()
    conn.close()
    return render_template('nomina/index.html', empleados=empleados, roles=roles)

@app.route('/nomina/empleado/nuevo', methods=['GET','POST'])
def empleado_nuevo():
    if request.method == 'POST':
        conn = get_db()
        ultimo = conn.execute("SELECT codigo FROM empleados ORDER BY id DESC LIMIT 1").fetchone()
        codigo = f"EMP-{(int(ultimo[0].replace('EMP-',''))+1):04d}" if ultimo else "EMP-0001"
        try:
            conn.execute('''INSERT INTO empleados
                (codigo,nombres,apellidos,cedula,cargo,departamento,salario_base,
                 fecha_ingreso,tipo_contrato,email,telefono,cuenta_bancaria)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?)''', (
                codigo, request.form['nombres'], request.form['apellidos'],
                request.form['cedula'], request.form['cargo'],
                request.form.get('departamento',''), float(request.form['salario_base']),
                request.form['fecha_ingreso'], request.form.get('tipo_contrato','Indefinido'),
                request.form.get('email',''), request.form.get('telefono',''),
                request.form.get('cuenta_bancaria','')
            ))
            conn.commit()
            flash('Empleado registrado.', 'success')
            return redirect(url_for('nomina'))
        except Exception as e:
            flash(f'Error: {e}', 'danger')
        finally:
            conn.close()
    return render_template('nomina/empleado_form.html')

@app.route('/nomina/rol/nuevo', methods=['GET','POST'])
def rol_nuevo():
    conn = get_db()
    empleados = conn.execute("SELECT * FROM empleados WHERE estado='Activo' ORDER BY apellidos").fetchall()
    if request.method == 'POST':
        salario = float(request.form['salario_base'])
        he_horas = float(request.form.get('horas_extra', 0))
        he_valor = round(salario / 240 * 1.5 * he_horas, 3)
        bonos = float(request.form.get('bonos', 0))
        iess_p = round(salario * 0.0945, 3)
        iess_pat = round(salario * 0.1215, 3)
        otros_desc = float(request.form.get('otros_descuentos', 0))
        liquido = round(salario + he_valor + bonos - iess_p - otros_desc, 3)
        try:
            conn.execute('''INSERT INTO roles_pago
                (empleado_id,periodo,salario_base,horas_extra,valor_horas_extra,bonos,
                 iess_personal,iess_patronal,otros_descuentos,liquido_recibir,estado)
                VALUES(?,?,?,?,?,?,?,?,?,?,?)''', (
                int(request.form['empleado_id']), request.form['periodo'],
                salario, he_horas, he_valor, bonos, iess_p, iess_pat, otros_desc,
                liquido, 'Generado'
            ))
            conn.commit()
            flash('Rol de pago generado.', 'success')
            return redirect(url_for('nomina'))
        except Exception as e:
            flash(f'Error: {e}', 'danger')
        finally:
            conn.close()
    conn.close()
    return render_template('nomina/rol_form.html', empleados=empleados, hoy=hoy())

# ─────────────────────────────────────────────
#  DECLARACIONES SRI  (Módulo 12)
# ─────────────────────────────────────────────
@app.route('/sri')
def sri():
    conn = get_db()
    declaraciones = conn.execute("SELECT * FROM declaraciones_sri ORDER BY periodo DESC").fetchall()
    conn.close()
    return render_template('sri/index.html', declaraciones=declaraciones)

@app.route('/sri/nueva', methods=['GET','POST'])
def sri_nueva():
    if request.method == 'POST':
        conn = get_db()
        periodo = request.form['periodo']
        tipo = request.form['tipo']
        vg = float(request.form.get('ventas_gravadas', 0))
        ve = float(request.form.get('ventas_exentas', 0))
        cc = float(request.form.get('compras_con_credito', 0))
        iva_c = round(vg * 0.15, 3)
        iva_p = round(cc * 0.15, 3)
        iva_pagar = round(max(iva_c - iva_p, 0), 3)
        ret_emit = float(request.form.get('retenciones_emitidas', 0))
        ret_rec = float(request.form.get('retenciones_recibidas', 0))
        try:
            conn.execute('''INSERT INTO declaraciones_sri
                (periodo,tipo,formulario,ventas_gravadas,ventas_exentas,compras_con_credito,
                 iva_cobrado,iva_pagado,iva_pagar,retenciones_emitidas,retenciones_recibidas,estado)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?)''', (
                periodo, tipo, request.form.get('formulario','104'),
                vg, ve, cc, iva_c, iva_p, iva_pagar, ret_emit, ret_rec, 'Borrador'
            ))
            conn.commit()
            flash('Declaración generada.', 'success')
            return redirect(url_for('sri'))
        except Exception as e:
            flash(f'Error: {e}', 'danger')
        finally:
            conn.close()
    # Auto-calcular desde facturas
    periodo_def = datetime.now().strftime('%Y-%m')
    conn = get_db()
    vg = conn.execute("SELECT COALESCE(SUM(subtotal),0) FROM facturas_venta WHERE fecha LIKE ? AND estado!='Anulada'", (f"{periodo_def}%",)).fetchone()[0]
    cc = conn.execute("SELECT COALESCE(SUM(subtotal),0) FROM facturas_compra WHERE fecha LIKE ?", (f"{periodo_def}%",)).fetchone()[0]
    conn.close()
    return render_template('sri/form.html', hoy=hoy(), periodo_def=periodo_def, vg=round(vg, 3), cc=round(cc, 3))

@app.route('/sri/<int:id>/presentar', methods=['POST'])
def sri_presentar(id):
    conn = get_db()
    conn.execute("UPDATE declaraciones_sri SET estado='Presentada', fecha_declaracion=? WHERE id=?", (hoy(), id))
    conn.commit(); conn.close()
    flash('Declaración marcada como presentada.', 'success')
    return redirect(url_for('sri'))

# ─────────────────────────────────────────────
#  TORNEOS Y EVENTOS  (Módulo 13)
# ─────────────────────────────────────────────
@app.route('/torneos')
def torneos():
    conn = get_db()
    torneos_list = conn.execute("SELECT * FROM torneos ORDER BY fecha_inicio DESC").fetchall()
    conn.close()
    return render_template('torneos/index.html', torneos=torneos_list)

@app.route('/torneos/nuevo', methods=['GET','POST'])
def torneo_nuevo():
    if request.method == 'POST':
        conn = get_db()
        try:
            conn.execute('''INSERT INTO torneos
                (nombre,tipo,fecha_inicio,fecha_fin,descripcion,presupuesto,estado)
                VALUES(?,?,?,?,?,?,?)''', (
                request.form['nombre'], request.form.get('tipo','Torneo'),
                request.form['fecha_inicio'], request.form['fecha_fin'],
                request.form.get('descripcion',''),
                float(request.form.get('presupuesto',0)),
                request.form.get('estado','Planificado')
            ))
            conn.commit()
            flash('Torneo/Evento registrado.', 'success')
            return redirect(url_for('torneos'))
        except Exception as e:
            flash(f'Error: {e}', 'danger')
        finally:
            conn.close()
    return render_template('torneos/form.html', hoy=hoy())

@app.route('/torneos/<int:id>')
def torneo_detalle(id):
    conn = get_db()
    torneo = conn.execute("SELECT * FROM torneos WHERE id=?", (id,)).fetchone()
    transacciones = conn.execute("SELECT * FROM torneo_transacciones WHERE torneo_id=? ORDER BY fecha DESC", (id,)).fetchall()
    ingresos = sum(t['monto'] for t in transacciones if t['tipo']=='Ingreso')
    egresos = sum(t['monto'] for t in transacciones if t['tipo']=='Egreso')
    conn.close()
    return render_template('torneos/detalle.html', torneo=torneo, transacciones=transacciones,
                           ingresos=ingresos, egresos=egresos, utilidad=ingresos-egresos)

@app.route('/torneos/<int:id>/transaccion', methods=['POST'])
def torneo_transaccion(id):
    conn = get_db()
    conn.execute('''INSERT INTO torneo_transacciones
        (torneo_id,fecha,tipo,concepto,monto,referencia)
        VALUES(?,?,?,?,?,?)''', (
        id, request.form['fecha'], request.form['tipo'],
        request.form['concepto'], float(request.form['monto']),
        request.form.get('referencia','')
    ))
    conn.commit(); conn.close()
    flash('Transacción registrada.', 'success')
    return redirect(url_for('torneo_detalle', id=id))

# ─────────────────────────────────────────────
#  PROFORMAS  (Módulo 04)
# ─────────────────────────────────────────────
@app.route('/proformas')
def proformas():
    conn = get_db()
    proformas_list = conn.execute("SELECT * FROM proformas ORDER BY fecha DESC").fetchall()
    conn.close()
    return render_template('proformas/index.html', proformas=proformas_list)

@app.route('/proformas/nueva', methods=['GET','POST'])
def proforma_nueva():
    if request.method == 'POST':
        conn = get_db()
        numero = sig_numero('proformas', 'numero', 'PRF')
        items_desc = request.form.getlist('item_desc[]')
        items_cant = request.form.getlist('item_cant[]')
        items_precio = request.form.getlist('item_precio[]')
        subtotal = sum(float(c)*float(p) for c,p in zip(items_cant, items_precio))
        iva_pct = float(request.form.get('iva_pct', 15))
        iva = round(subtotal * iva_pct / 100, 3)
        total = round(subtotal + iva, 3)
        try:
            cur = conn.execute('''INSERT INTO proformas
                (numero,fecha,validez_dias,cliente_nombre,cliente_email,objeto,subtotal,iva,total,estado,observaciones)
                VALUES(?,?,?,?,?,?,?,?,?,?,?)''', (
                numero, request.form['fecha'], int(request.form.get('validez_dias',30)),
                request.form['cliente_nombre'], request.form.get('cliente_email',''),
                request.form.get('objeto',''), round(subtotal, 3), iva, total,
                'Emitida', request.form.get('observaciones','')
            ))
            pid = cur.lastrowid
            for d,c,p in zip(items_desc, items_cant, items_precio):
                if d.strip():
                    conn.execute('''INSERT INTO proforma_items
                        (proforma_id,descripcion,cantidad,precio_unitario,subtotal)
                        VALUES(?,?,?,?,?)''', (pid, d, float(c), float(p), float(c)*float(p)))
            conn.commit()
            flash(f'Proforma {numero} emitida.', 'success')
            return redirect(url_for('proformas'))
        except Exception as e:
            flash(f'Error: {e}', 'danger')
        finally:
            conn.close()
    numero_preview = sig_numero('proformas', 'numero', 'PRF')
    return render_template('proformas/form.html', numero=numero_preview, hoy=hoy())

@app.route('/proformas/<int:id>')
def proforma_detalle(id):
    conn = get_db()
    proforma = conn.execute("SELECT * FROM proformas WHERE id=?", (id,)).fetchone()
    items = conn.execute("SELECT * FROM proforma_items WHERE proforma_id=?", (id,)).fetchall()
    conn.close()
    return render_template('proformas/detalle.html', proforma=proforma, items=items)

# ─────────────────────────────────────────────
#  REPORTES  (Módulo 02 & 03)
# ─────────────────────────────────────────────
@app.route('/reportes')
def reportes():
    return render_template('reportes/index.html')

@app.route('/reportes/diario')
def reporte_diario():
    fecha_ini = request.args.get('fecha_ini', hoy())
    fecha_fin = request.args.get('fecha_fin', hoy())
    conn = get_db()
    ventas = conn.execute("""SELECT 'Venta' as tipo, numero, fecha, cliente_nombre as contraparte,
        total FROM facturas_venta WHERE fecha BETWEEN ? AND ? AND estado!='Anulada'
        UNION ALL
        SELECT 'Compra', numero, fecha, proveedor_nombre, total FROM facturas_compra
        WHERE fecha BETWEEN ? AND ?
        ORDER BY fecha""", (fecha_ini, fecha_fin, fecha_ini, fecha_fin)).fetchall()
    conn.close()
    return render_template('reportes/diario.html', movimientos=ventas,
                           fecha_ini=fecha_ini, fecha_fin=fecha_fin)

@app.route('/reportes/balance-general')
def balance_general():
    conn = get_db()
    ventas_tot = conn.execute("SELECT COALESCE(SUM(total),0) FROM facturas_venta WHERE estado!='Anulada'").fetchone()[0]
    compras_tot = conn.execute("SELECT COALESCE(SUM(total),0) FROM facturas_compra").fetchone()[0]
    cuotas_tot = conn.execute("SELECT COALESCE(SUM(total),0) FROM cuotas WHERE estado='Pagada'").fetchone()[0]
    cxc = conn.execute("SELECT COALESCE(SUM(saldo),0) FROM cuentas_cobrar WHERE estado!='Pagada'").fetchone()[0]
    cxp = conn.execute("SELECT COALESCE(SUM(saldo),0) FROM cuentas_pagar WHERE estado!='Pagada'").fetchone()[0]
    inventario_val = conn.execute("SELECT COALESCE(SUM(stock_actual*precio_costo),0) FROM inventario").fetchone()[0]
    conn.close()
    caja = ventas_tot + cuotas_tot - compras_tot
    total_activos = max(caja,0) + cxc + inventario_val
    total_pasivos = cxp
    patrimonio = total_activos - total_pasivos
    return render_template('reportes/balance_general.html',
        caja=caja, cxc=cxc, inventario_val=inventario_val,
        total_activos=total_activos, cxp=cxp, total_pasivos=total_pasivos,
        patrimonio=patrimonio, fecha=hoy()
    )

@app.route('/reportes/estado-resultados')
def estado_resultados():
    mes = request.args.get('mes', datetime.now().strftime('%Y-%m'))
    conn = get_db()
    ing_ventas = conn.execute("SELECT COALESCE(SUM(total),0) FROM facturas_venta WHERE fecha LIKE ? AND estado!='Anulada'", (f"{mes}%",)).fetchone()[0]
    ing_cuotas = conn.execute("SELECT COALESCE(SUM(total),0) FROM cuotas WHERE fecha_pago LIKE ? AND estado='Pagada'", (f"{mes}%",)).fetchone()[0]
    ing_torneos = conn.execute("SELECT COALESCE(SUM(monto),0) FROM torneo_transacciones WHERE tipo='Ingreso' AND fecha LIKE ?", (f"{mes}%",)).fetchone()[0]
    total_ingresos = ing_ventas + ing_cuotas + ing_torneos
    gasto_compras = conn.execute("SELECT COALESCE(SUM(total),0) FROM facturas_compra WHERE fecha LIKE ?", (f"{mes}%",)).fetchone()[0]
    gasto_nomina = conn.execute("SELECT COALESCE(SUM(liquido_recibir),0) FROM roles_pago WHERE periodo=?", (mes,)).fetchone()[0]
    gasto_torneos = conn.execute("SELECT COALESCE(SUM(monto),0) FROM torneo_transacciones WHERE tipo='Egreso' AND fecha LIKE ?", (f"{mes}%",)).fetchone()[0]
    total_gastos = gasto_compras + gasto_nomina + gasto_torneos
    utilidad = total_ingresos - total_gastos
    conn.close()
    return render_template('reportes/estado_resultados.html',
        mes=mes, ing_ventas=ing_ventas, ing_cuotas=ing_cuotas, ing_torneos=ing_torneos,
        total_ingresos=total_ingresos, gasto_compras=gasto_compras, gasto_nomina=gasto_nomina,
        gasto_torneos=gasto_torneos, total_gastos=total_gastos, utilidad=utilidad
    )

@app.route('/reportes/socios-mora')
def reporte_socios_mora():
    conn = get_db()
    datos = conn.execute("""
        SELECT s.codigo, s.nombres||' '||s.apellidos as nombre, s.email, s.telefono,
               COUNT(c.id) as cuotas_pendientes,
               COALESCE(SUM(c.monto),0) as monto_total
        FROM socios s
        JOIN cuotas c ON c.socio_id=s.id
        WHERE c.estado='Pendiente' AND c.fecha_vencimiento < ?
        GROUP BY s.id ORDER BY monto_total DESC
    """, (hoy(),)).fetchall()
    conn.close()
    return render_template('reportes/socios_mora.html', datos=datos, hoy=hoy())

# ─────────────────────────────────────────────
#  PLAN DE CUENTAS
# ─────────────────────────────────────────────
@app.route('/plan-cuentas')
def plan_cuentas():
    conn = get_db()
    cuentas = conn.execute("SELECT * FROM plan_cuentas ORDER BY codigo").fetchall()
    conn.close()
    return render_template('plan_cuentas/index.html', cuentas=cuentas)

@app.route('/plan-cuentas/nueva', methods=['GET','POST'])
def cuenta_nueva():
    if request.method == 'POST':
        conn = get_db()
        try:
            conn.execute('''INSERT INTO plan_cuentas
                (codigo,nombre,tipo,naturaleza,nivel) VALUES(?,?,?,?,?)''', (
                request.form['codigo'], request.form['nombre'],
                request.form['tipo'], request.form['naturaleza'],
                int(request.form.get('nivel',3))
            ))
            conn.commit()
            flash('Cuenta registrada.', 'success')
            return redirect(url_for('plan_cuentas'))
        except Exception as e:
            flash(f'Error: {e}', 'danger')
        finally:
            conn.close()
    return render_template('plan_cuentas/form.html')

# ─────────────────────────────────────────────
@app.route('/asientos')
def asientos():
    fecha_ini = request.args.get('fecha_ini', datetime.now().strftime('%Y-%m-01'))
    fecha_fin = request.args.get('fecha_fin', hoy())
    conn = get_db()
    asientos_list = conn.execute("""
        SELECT a.*,
               COALESCE(SUM(d.debe),0) as total_debe,
               COALESCE(SUM(d.haber),0) as total_haber
        FROM asientos a
        LEFT JOIN asiento_detalles d ON d.asiento_id=a.id
        WHERE a.fecha BETWEEN ? AND ?
        GROUP BY a.id
        ORDER BY a.fecha DESC, a.numero DESC
    """, (fecha_ini, fecha_fin)).fetchall()
    conn.close()
    return render_template('asientos/index.html', asientos=asientos_list, fecha_ini=fecha_ini, fecha_fin=fecha_fin)

@app.route('/asientos/nuevo', methods=['GET','POST'])
def asiento_nuevo():
    conn = get_db()
    cuentas = conn.execute("SELECT * FROM plan_cuentas WHERE activa=1 ORDER BY codigo").fetchall()
    if request.method == 'POST':
        cuenta_ids = request.form.getlist('cuenta_id[]')
        descripciones = request.form.getlist('detalle_desc[]')
        debes = request.form.getlist('debe[]')
        haberes = request.form.getlist('haber[]')
        detalles = []
        total_debe = 0.0
        total_haber = 0.0
        for cuenta_id, desc, debe, haber in zip(cuenta_ids, descripciones, debes, haberes):
            debe_val = float(debe or 0)
            haber_val = float(haber or 0)
            if cuenta_id and (debe_val > 0 or haber_val > 0):
                detalles.append((int(cuenta_id), desc, debe_val, haber_val))
                total_debe += debe_val
                total_haber += haber_val
        if len(detalles) < 2:
            flash('El asiento debe tener al menos dos lineas.', 'danger')
        elif round(total_debe, 3) != round(total_haber, 3):
            flash('El asiento no cuadra: debe y haber deben ser iguales.', 'danger')
        else:
            try:
                numero = sig_numero('asientos', 'numero', 'ASI')
                cur = conn.execute('''INSERT INTO asientos
                    (numero,fecha,concepto,tipo,referencia_tipo)
                    VALUES(?,?,?,?,?)''', (
                    numero, request.form['fecha'], request.form['concepto'],
                    request.form.get('tipo','manual'), request.form.get('referencia_tipo','manual')
                ))
                asiento_id = cur.lastrowid
                for cuenta_id, desc, debe_val, haber_val in detalles:
                    conn.execute('''INSERT INTO asiento_detalles
                        (asiento_id,cuenta_id,descripcion,debe,haber)
                        VALUES(?,?,?,?,?)''', (
                        asiento_id, cuenta_id, desc, debe_val, haber_val
                    ))
                conn.commit()
                flash(f'Asiento {numero} registrado correctamente.', 'success')
                return redirect(url_for('asiento_detalle', id=asiento_id))
            except Exception as e:
                flash(f'Error: {e}', 'danger')
    conn.close()
    numero_preview = sig_numero('asientos', 'numero', 'ASI')
    return render_template('asientos/form.html', cuentas=cuentas, hoy=hoy(), numero=numero_preview)

@app.route('/asientos/<int:id>')
def asiento_detalle(id):
    conn = get_db()
    asiento = conn.execute("SELECT * FROM asientos WHERE id=?", (id,)).fetchone()
    detalles = conn.execute("""
        SELECT d.*, p.codigo, p.nombre
        FROM asiento_detalles d
        JOIN plan_cuentas p ON p.id=d.cuenta_id
        WHERE d.asiento_id=?
        ORDER BY d.id
    """, (id,)).fetchall()
    conn.close()
    return render_template('asientos/detalle.html', asiento=asiento, detalles=detalles)

@app.route('/reportes/diario-contable')
def diario_contable():
    fecha_ini = request.args.get('fecha_ini', datetime.now().strftime('%Y-%m-01'))
    fecha_fin = request.args.get('fecha_fin', hoy())
    conn = get_db()
    filas = conn.execute("""
        SELECT a.numero, a.fecha, a.concepto, a.tipo,
               p.codigo, p.nombre as cuenta,
               d.descripcion, d.debe, d.haber
        FROM asientos a
        JOIN asiento_detalles d ON d.asiento_id=a.id
        JOIN plan_cuentas p ON p.id=d.cuenta_id
        WHERE a.fecha BETWEEN ? AND ?
        ORDER BY a.fecha, a.numero, d.id
    """, (fecha_ini, fecha_fin)).fetchall()
    total_debe = sum(row['debe'] for row in filas)
    total_haber = sum(row['haber'] for row in filas)
    conn.close()
    return render_template('reportes/diario_contable.html', filas=filas, fecha_ini=fecha_ini,
                           fecha_fin=fecha_fin, total_debe=total_debe, total_haber=total_haber)

@app.route('/reportes/mayor')
def mayor_contable():
    cuenta_id = request.args.get('cuenta_id','')
    fecha_ini = request.args.get('fecha_ini', datetime.now().strftime('%Y-%m-01'))
    fecha_fin = request.args.get('fecha_fin', hoy())
    conn = get_db()
    cuentas = conn.execute("SELECT * FROM plan_cuentas WHERE activa=1 ORDER BY codigo").fetchall()
    movimientos = []
    cuenta = None
    saldo = 0.0
    if cuenta_id:
        cuenta = conn.execute("SELECT * FROM plan_cuentas WHERE id=?", (cuenta_id,)).fetchone()
        movimientos = conn.execute("""
            SELECT a.numero, a.fecha, a.concepto, d.descripcion, d.debe, d.haber
            FROM asiento_detalles d
            JOIN asientos a ON a.id=d.asiento_id
            WHERE d.cuenta_id=? AND a.fecha BETWEEN ? AND ?
            ORDER BY a.fecha, a.numero, d.id
        """, (cuenta_id, fecha_ini, fecha_fin)).fetchall()
    conn.close()
    filas = []
    for mov in movimientos:
        if cuenta and cuenta['naturaleza'] == 'Acreedora':
            saldo += mov['haber'] - mov['debe']
        else:
            saldo += mov['debe'] - mov['haber']
        filas.append((mov, saldo))
    return render_template('reportes/mayor.html', cuentas=cuentas, cuenta=cuenta, filas=filas,
                           cuenta_id=cuenta_id, fecha_ini=fecha_ini, fecha_fin=fecha_fin, saldo=saldo)

# ─────────────────────────────────────────────
create_app()

if __name__ == '__main__':
    app.run(debug=os.environ.get('FLASK_DEBUG') == '1', host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
