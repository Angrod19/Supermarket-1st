import hashlib
import hmac
import os
import sqlite3
import time
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

DB_PATH = "supermercado.db"
SCHEMA_PATH = "schema.sql"
MAX_INTENTOS_ANTES_BLOQUEO = 3
SEGUNDOS_BLOQUEO_BASE = 15  # Escala: 15s, 30s, 60s...


def crear_hash_password(password: str, salt_hex: str | None = None) -> tuple[str, str]:
    if salt_hex is None:
        salt_bytes = os.urandom(16)
        salt_hex = salt_bytes.hex()
    else:
        salt_bytes = bytes.fromhex(salt_hex)

    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt_bytes,
        200_000,
    )
    return dk.hex(), salt_hex


def verificar_password(password: str, hash_guardado: str, salt_hex: str) -> bool:
    hash_calculado, _ = crear_hash_password(password, salt_hex)
    return hmac.compare_digest(hash_calculado, hash_guardado)


class BaseDatosLocal:
    def __init__(self, db_path: str = DB_PATH, schema_path: str = SCHEMA_PATH):
        self.db_path = db_path
        self.schema_path = schema_path
        self._inicializar_bd()

    def _conectar(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _inicializar_bd(self):
        with self._conectar() as conn:
            if os.path.exists(self.schema_path):
                with open(self.schema_path, "r", encoding="utf-8") as f:
                    conn.executescript(f.read())
            else:
                conn.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS usuarios (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT NOT NULL UNIQUE,
                        password_hash TEXT NOT NULL,
                        salt TEXT NOT NULL,
                        rol TEXT NOT NULL CHECK (rol IN ('administrador', 'supervisor', 'cajero')),
                        intentos_fallidos INTEGER NOT NULL DEFAULT 0,
                        bloqueado_hasta REAL NOT NULL DEFAULT 0.0,
                        activo INTEGER NOT NULL DEFAULT 1
                    );
                    CREATE TABLE IF NOT EXISTS productos (
                        codigo TEXT PRIMARY KEY,
                        nombre TEXT NOT NULL,
                        precio REAL NOT NULL CHECK (precio >= 0),
                        stock INTEGER NOT NULL CHECK (stock >= 0)
                    );
                    CREATE TABLE IF NOT EXISTS ventas (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        fecha_hora TEXT NOT NULL,
                        cajero_username TEXT NOT NULL,
                        medio_pago TEXT NOT NULL CHECK (medio_pago IN ('Efectivo', 'Débito', 'Crédito')),
                        subtotal REAL NOT NULL CHECK (subtotal >= 0),
                        total REAL NOT NULL CHECK (total >= 0),
                        FOREIGN KEY (cajero_username) REFERENCES usuarios(username)
                    );
                    CREATE TABLE IF NOT EXISTS venta_detalle (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        venta_id INTEGER NOT NULL,
                        producto_codigo TEXT NOT NULL,
                        cantidad INTEGER NOT NULL CHECK (cantidad > 0),
                        precio_unitario REAL NOT NULL CHECK (precio_unitario >= 0),
                        FOREIGN KEY (venta_id) REFERENCES ventas(id) ON DELETE CASCADE,
                        FOREIGN KEY (producto_codigo) REFERENCES productos(codigo)
                    );
                    CREATE TABLE IF NOT EXISTS auditoria_seguridad (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        fecha_hora TEXT NOT NULL,
                        username_intentado TEXT NOT NULL,
                        evento TEXT NOT NULL,
                        detalle TEXT NOT NULL
                    );
                    """
                )

            # Crear cuentas iniciales solo si no existen usuarios
            cur = conn.execute("SELECT COUNT(*) AS total FROM usuarios")
            if cur.fetchone()["total"] == 0:
                semilla_usuarios = [
                    ("admin", "Admin#2026!", "administrador"),
                    ("super", "Super#2026!", "supervisor"),
                    ("cajero1", "Caja#2026!", "cajero"),
                ]
                for user, clave, rol in semilla_usuarios:
                    h, s = crear_hash_password(clave)
                    conn.execute(
                        """
                        INSERT INTO usuarios (username, password_hash, salt, rol)
                        VALUES (?, ?, ?, ?)
                        """,
                        (user, h, s, rol),
                    )

            # Productos iniciales si la tabla está vacía
            cur_p = conn.execute("SELECT COUNT(*) AS total FROM productos")
            if cur_p.fetchone()["total"] == 0:
                productos_iniciales = [
                    ("P001", "Leche 1L", 1200.00, 50),
                    ("P002", "Pan Lactal", 1500.00, 30),
                    ("P003", "Arroz 1kg", 950.00, 40),
                    ("P004", "Aceite Girasol 900ml", 2100.00, 25),
                ]
                conn.executemany(
                    "INSERT INTO productos (codigo, nombre, precio, stock) VALUES (?, ?, ?, ?)",
                    productos_iniciales,
                )
            conn.commit()

    def registrar_auditoria(self, username: str, evento: str, detalle: str):
        ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._conectar() as conn:
            conn.execute(
                """
                INSERT INTO auditoria_seguridad (fecha_hora, username_intentado, evento, detalle)
                VALUES (?, ?, ?, ?)
                """,
                (ahora, username, evento, detalle),
            )
            conn.commit()

    def autenticar_usuario(self, username: str, password: str) -> tuple[bool, dict | None, str]:
        ahora = time.time()
        # Pequeño retardo base para frenar escaneos rápidos
        time.sleep(0.35)

        with self._conectar() as conn:
            fila = conn.execute(
                """
                SELECT id, username, password_hash, salt, rol, intentos_fallidos, bloqueado_hasta, activo
                FROM usuarios
                WHERE username = ?
                """,
                (username,),
            ).fetchone()

            if not fila or not fila["activo"]:
                self.registrar_auditoria(username or "(vacio)", "LOGIN_FALLIDO", "Usuario inexistente o inactivo")
                return False, None, "Credenciales inválidas."

            if fila["bloqueado_hasta"] > ahora:
                restante = int(fila["bloqueado_hasta"] - ahora) + 1
                self.registrar_auditoria(username, "LOGIN_BLOQUEADO", f"Bloqueado por {restante}s adicionales")
                return False, None, f"Cuenta bloqueada temporalmente. Intente en {restante} segundos."

            if verificar_password(password, fila["password_hash"], fila["salt"]):
                conn.execute(
                    """
                    UPDATE usuarios
                    SET intentos_fallidos = 0, bloqueado_hasta = 0.0
                    WHERE id = ?
                    """,
                    (fila["id"],),
                )
                conn.commit()
                self.registrar_auditoria(username, "LOGIN_OK", f"Rol: {fila['rol']}")
                return True, {"username": fila["username"], "rol": fila["rol"]}, "Acceso concedido."

            intentos = fila["intentos_fallidos"] + 1
            bloqueo_hasta = 0.0
            mensaje = "Credenciales inválidas."

            if intentos >= MAX_INTENTOS_ANTES_BLOQUEO:
                exceso = intentos - MAX_INTENTOS_ANTES_BLOQUEO
                duracion = SEGUNDOS_BLOQUEO_BASE * (2 ** min(exceso, 5))
                bloqueo_hasta = ahora + duracion
                mensaje = f"Demasiados intentos fallidos. Cuenta bloqueada por {duracion} segundos."
                self.registrar_auditoria(username, "CUENTA_BLOQUEADA", f"Bloqueo de {duracion}s (intento #{intentos})")
            else:
                self.registrar_auditoria(username, "LOGIN_FALLIDO", f"Intento fallido #{intentos}")

            conn.execute(
                """
                UPDATE usuarios
                SET intentos_fallidos = ?, bloqueado_hasta = ?
                WHERE id = ?
                """,
                (intentos, bloqueo_hasta, fila["id"]),
            )
            conn.commit()
            return False, None, mensaje

    def obtener_productos(self) -> list[dict]:
        with self._conectar() as conn:
            filas = conn.execute(
                "SELECT codigo, nombre, precio, stock FROM productos ORDER BY codigo ASC"
            ).fetchall()
            return [dict(f) for f in filas]

    def alta_producto(self, codigo: str, nombre: str, precio: float, stock: int, actor: str) -> tuple[bool, str]:
        try:
            with self._conectar() as conn:
                conn.execute(
                    "INSERT INTO productos (codigo, nombre, precio, stock) VALUES (?, ?, ?, ?)",
                    (codigo, nombre, precio, stock),
                )
                conn.commit()
            self.registrar_auditoria(actor, "ALTA_PRODUCTO", f"{codigo} - {nombre} (${precio:.2f}, stock={stock})")
            return True, "Producto registrado en la base de datos."
        except sqlite3.IntegrityError:
            return False, f"Ya existe un producto con el código '{codigo}' o los valores no son válidos."

    def modificar_producto(
        self,
        codigo: str,
        stock: int,
        actor: str,
        nombre: str | None = None,
        precio: float | None = None,
    ) -> tuple[bool, str]:
        with self._conectar() as conn:
            actual = conn.execute(
                "SELECT codigo, nombre, precio, stock FROM productos WHERE codigo = ?",
                (codigo,),
            ).fetchone()
            if not actual:
                return False, "El producto no existe."

            nuevo_nombre = actual["nombre"] if nombre is None else nombre
            nuevo_precio = actual["precio"] if precio is None else precio

            conn.execute(
                """
                UPDATE productos
                SET nombre = ?, precio = ?, stock = ?
                WHERE codigo = ?
                """,
                (nuevo_nombre, nuevo_precio, stock, codigo),
            )
            conn.commit()

        self.registrar_auditoria(
            actor,
            "MODIFICAR_PRODUCTO",
            f"{codigo}: stock {actual['stock']}->{stock}, precio=${nuevo_precio:.2f}",
        )
        return True, "Cambios guardados en SQLite."

    def baja_producto(self, codigo: str, actor: str) -> tuple[bool, str]:
        with self._conectar() as conn:
            cur = conn.execute("DELETE FROM productos WHERE codigo = ?", (codigo,))
            conn.commit()
            if cur.rowcount == 0:
                return False, "Producto no encontrado."

        self.registrar_auditoria(actor, "BAJA_PRODUCTO", f"Eliminado código {codigo}")
        return True, "Producto dado de baja."

    def registrar_venta(self, cajero: str, medio_pago: str, items: list[dict], subtotal: float, total: float) -> tuple[bool, str]:
        fecha_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            with self._conectar() as conn:
                conn.execute("BEGIN IMMEDIATE")

                # Verificar stock actualizado dentro de la transacción
                for item in items:
                    fila = conn.execute(
                        "SELECT stock, nombre, precio FROM productos WHERE codigo = ?",
                        (item["codigo"],),
                    ).fetchone()
                    if not fila or fila["stock"] < item["cantidad"]:
                        conn.rollback()
                        return False, f"Stock insuficiente para '{item['nombre']}'."

                cur_venta = conn.execute(
                    """
                    INSERT INTO ventas (fecha_hora, cajero_username, medio_pago, subtotal, total)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (fecha_hora, cajero, medio_pago, subtotal, total),
                )
                venta_id = cur_venta.lastrowid

                for item in items:
                    conn.execute(
                        """
                        INSERT INTO venta_detalle (venta_id, producto_codigo, cantidad, precio_unitario)
                        VALUES (?, ?, ?, ?)
                        """,
                        (venta_id, item["codigo"], item["cantidad"], item["precio"]),
                    )
                    conn.execute(
                        """
                        UPDATE productos
                        SET stock = stock - ?
                        WHERE codigo = ?
                        """,
                        (item["cantidad"], item["codigo"]),
                    )

                conn.commit()

            self.registrar_auditoria(cajero, "VENTA_REGISTRADA", f"Venta #{venta_id} - {medio_pago} - Total ${total:.2f}")
            return True, f"Venta #{venta_id} guardada en SQL y stock descontado."
        except sqlite3.Error as exc:
            return False, f"Error de base de datos al registrar venta: {exc}"


class SupermercadoApp:
    BG_PRINCIPAL = "#E6E8EB"
    BG_PANEL = "#FFFFFF"
    BG_HEADER = "#1F2933"
    BG_ACENTO = "#2B3A4A"
    FG_CLARO = "#FFFFFF"
    FG_TEXTO = "#111827"
    BORDE = "#9CA3AF"

    def __init__(self, root: tk.Tk, bd: BaseDatosLocal):
        self.root = root
        self.bd = bd
        self.root.title("SUPERMERCADO - TERMINAL LOCAL SQL")
        self.root.geometry("1060x690")
        self.root.minsize(940, 620)
        self.root.configure(bg=self.BG_PRINCIPAL)

        self.usuario_actual = None
        self.carrito = []

        self._configurar_estilos_rectos()
        self.mostrar_pantalla_login()

    def _configurar_estilos_rectos(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(
            "Recto.Treeview",
            background="#FFFFFF",
            foreground=self.FG_TEXTO,
            fieldbackground="#FFFFFF",
            rowheight=28,
            borderwidth=1,
            relief="solid",
            font=("Consolas", 10),
        )
        style.configure(
            "Recto.Treeview.Heading",
            background=self.BG_ACENTO,
            foreground=self.FG_CLARO,
            relief="flat",
            borderwidth=1,
            font=("Segoe UI", 10, "bold"),
        )
        style.map("Recto.Treeview.Heading", background=[("active", self.BG_HEADER)])

    def _limpiar_ventana(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def _btn_recto(self, parent, texto, comando, bg=BG_ACENTO, fg=FG_CLARO):
        return tk.Button(
            parent,
            text=texto,
            command=comando,
            bg=bg,
            fg=fg,
            activebackground=self.BG_HEADER,
            activeforeground=self.FG_CLARO,
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground=self.BG_HEADER,
            font=("Segoe UI", 10, "bold"),
            cursor="hand2",
            padx=14,
            pady=7,
        )

    def _entrada_recta(self, parent, show=None, width=26):
        return tk.Entry(
            parent,
            show=show,
            width=width,
            bg="#FFFFFF",
            fg=self.FG_TEXTO,
            insertbackground=self.FG_TEXTO,
            relief="solid",
            bd=1,
            highlightthickness=0,
            font=("Consolas", 11),
        )

    def mostrar_pantalla_login(self):
        self._limpiar_ventana()
        self.usuario_actual = None
        self.carrito = []

        marco_externo = tk.Frame(self.root, bg=self.BG_PRINCIPAL)
        marco_externo.pack(expand=True, fill="both")

        caja_login = tk.Frame(
            marco_externo,
            bg=self.BG_PANEL,
            highlightbackground=self.BG_HEADER,
            highlightthickness=2,
            padx=36,
            pady=30,
        )
        caja_login.place(relx=0.5, rely=0.5, anchor="center")

        cabecera = tk.Frame(caja_login, bg=self.BG_HEADER, padx=16, pady=12)
        cabecera.pack(fill="x", pady=(0, 20))
        tk.Label(
            cabecera,
            text="SUPERMERCADO // ACCESO SEGURO SQL",
            bg=self.BG_HEADER,
            fg=self.FG_CLARO,
            font=("Segoe UI", 12, "bold"),
        ).pack()

        tk.Label(
            caja_login,
            text="USUARIO",
            bg=self.BG_PANEL,
            fg=self.FG_TEXTO,
            font=("Segoe UI", 9, "bold"),
            anchor="w",
        ).pack(fill="x")
        entry_user = self._entrada_recta(caja_login, width=34)
        entry_user.pack(fill="x", pady=(4, 12), ipady=4)
        entry_user.focus_set()

        tk.Label(
            caja_login,
            text="CONTRASEÑA",
            bg=self.BG_PANEL,
            fg=self.FG_TEXTO,
            font=("Segoe UI", 9, "bold"),
            anchor="w",
        ).pack(fill="x")
        entry_pass = self._entrada_recta(caja_login, show="*", width=34)
        entry_pass.pack(fill="x", pady=(4, 18), ipady=4)

        def intentar_login(event=None):
            u = entry_user.get().strip()
            p = entry_pass.get().strip()
            ok, usuario, msg = self.bd.autenticar_usuario(u, p)
            if ok and usuario:
                self.usuario_actual = usuario
                self.mostrar_panel_principal()
            else:
                messagebox.showerror("Acceso denegado", msg)

        entry_pass.bind("<Return>", intentar_login)
        self._btn_recto(caja_login, "INICIAR SESIÓN", intentar_login).pack(fill="x")

        ayuda = tk.Frame(
            caja_login,
            bg=self.BG_PRINCIPAL,
            highlightbackground=self.BORDE,
            highlightthickness=1,
            padx=12,
            pady=10,
        )
        ayuda.pack(fill="x", pady=(18, 0))
        tk.Label(
            ayuda,
            text=(
                "Cuentas iniciales (hash PBKDF2 en SQLite)\n"
                "• admin   / Admin#2026!  -> Administrador\n"
                "• super   / Super#2026!  -> Supervisor\n"
                "• cajero1 / Caja#2026!   -> Cajero\n"
                "* 3 fallos bloquean temporalmente la cuenta."
            ),
            bg=self.BG_PRINCIPAL,
            fg=self.FG_TEXTO,
            font=("Consolas", 9),
            justify="left",
            anchor="w",
        ).pack(fill="x")

    def mostrar_panel_principal(self):
        self._limpiar_ventana()
        rol = self.usuario_actual["rol"]

        barra_top = tk.Frame(
            self.root,
            bg=self.BG_HEADER,
            height=52,
            padx=18,
            highlightbackground=self.BG_HEADER,
            highlightthickness=1,
        )
        barra_top.pack(fill="x", side="top")
        barra_top.pack_propagate(False)

        tk.Label(
            barra_top,
            text=f"SQL LOCAL ({DB_PATH})  |  USUARIO: {self.usuario_actual['username'].upper()}  |  ROL: {rol.upper()}",
            bg=self.BG_HEADER,
            fg=self.FG_CLARO,
            font=("Segoe UI", 10, "bold"),
        ).pack(side="left")

        self._btn_recto(
            barra_top,
            "CERRAR SESIÓN",
            self.mostrar_pantalla_login,
            bg="#7F1D1D",
        ).pack(side="right")

        cuerpo = tk.Frame(self.root, bg=self.BG_PRINCIPAL, padx=16, pady=16)
        cuerpo.pack(expand=True, fill="both")

        if rol == "administrador":
            self._construir_vista_admin_o_supervisor(cuerpo, es_admin=True)
        elif rol == "supervisor":
            self._construir_vista_admin_o_supervisor(cuerpo, es_admin=False)
        elif rol == "cajero":
            self._construir_vista_cajero(cuerpo)

    def _construir_vista_admin_o_supervisor(self, parent, es_admin: bool):
        panel_izq = tk.Frame(
            parent,
            bg=self.BG_PANEL,
            highlightbackground=self.BORDE,
            highlightthickness=1,
            padx=14,
            pady=14,
        )
        panel_izq.pack(side="left", expand=True, fill="both", padx=(0, 8))

        titulo_izq = "STOCK GENERAL (ADMINISTRACIÓN SQL)" if es_admin else "STOCK GENERAL (SUPERVISIÓN SQL)"
        tk.Label(
            panel_izq,
            text=titulo_izq,
            bg=self.BG_ACENTO,
            fg=self.FG_CLARO,
            font=("Segoe UI", 10, "bold"),
            padx=10,
            pady=6,
            anchor="w",
        ).pack(fill="x", pady=(0, 10))

        cols = ("codigo", "nombre", "precio", "stock")
        tabla = ttk.Treeview(panel_izq, columns=cols, show="headings", style="Recto.Treeview")
        tabla.heading("codigo", text="CÓDIGO")
        tabla.heading("nombre", text="PRODUCTO")
        tabla.heading("precio", text="PRECIO")
        tabla.heading("stock", text="STOCK")
        tabla.column("codigo", width=95, anchor="center")
        tabla.column("nombre", width=230, anchor="w")
        tabla.column("precio", width=110, anchor="e")
        tabla.column("stock", width=85, anchor="center")
        tabla.pack(expand=True, fill="both")

        panel_der = tk.Frame(
            parent,
            bg=self.BG_PANEL,
            highlightbackground=self.BORDE,
            highlightthickness=1,
            width=350,
            padx=16,
            pady=14,
        )
        panel_der.pack(side="right", fill="y", padx=(8, 0))
        panel_der.pack_propagate(False)

        tk.Label(
            panel_der,
            text="OPERACIONES DE INVENTARIO",
            bg=self.BG_ACENTO,
            fg=self.FG_CLARO,
            font=("Segoe UI", 10, "bold"),
            padx=10,
            pady=6,
            anchor="w",
        ).pack(fill="x", pady=(0, 14))

        def campo(etiqueta):
            tk.Label(
                panel_der,
                text=etiqueta,
                bg=self.BG_PANEL,
                fg=self.FG_TEXTO,
                font=("Segoe UI", 9, "bold"),
                anchor="w",
            ).pack(fill="x", pady=(6, 2))
            e = self._entrada_recta(panel_der, width=28)
            e.pack(fill="x", ipady=3)
            return e

        e_codigo = campo("CÓDIGO DE PRODUCTO")
        e_nombre = campo("NOMBRE DEL PRODUCTO")
        e_precio = campo("PRECIO UNITARIO ($)")
        e_stock = campo("CANTIDAD EN STOCK")

        if not es_admin:
            e_nombre.configure(state="disabled", bg=self.BG_PRINCIPAL)
            e_precio.configure(state="disabled", bg=self.BG_PRINCIPAL)

        def refrescar_tabla():
            for fila in tabla.get_children():
                tabla.delete(fila)
            for p in self.bd.obtener_productos():
                tabla.insert("", "end", values=(p["codigo"], p["nombre"], f"{p['precio']:.2f}", p["stock"]))

        def limpiar_campos():
            e_codigo.configure(state="normal")
            for widget in (e_codigo, e_nombre, e_precio, e_stock):
                if str(widget["state"]) != "disabled":
                    widget.delete(0, "end")

        def al_seleccionar(event=None):
            sel = tabla.selection()
            if not sel:
                return
            vals = tabla.item(sel[0], "values")
            e_codigo.configure(state="normal")
            e_codigo.delete(0, "end")
            e_codigo.insert(0, vals[0])
            if es_admin:
                e_codigo.configure(state="readonly")
                e_nombre.delete(0, "end")
                e_nombre.insert(0, vals[1])
                e_precio.delete(0, "end")
                e_precio.insert(0, vals[2])
            e_stock.delete(0, "end")
            e_stock.insert(0, vals[3])

        tabla.bind("<<TreeviewSelect>>", al_seleccionar)

        def alta_producto():
            if not es_admin:
                messagebox.showwarning("Permiso restringido", "Solo el Administrador puede dar de alta.")
                return
            cod = e_codigo.get().strip().upper()
            nom = e_nombre.get().strip()
            try:
                pre = float(e_precio.get().strip())
                stk = int(e_stock.get().strip())
            except ValueError:
                messagebox.showerror("Dato inválido", "Precio numérico y stock entero.")
                return
            if not cod or not nom or pre < 0 or stk < 0:
                messagebox.showerror("Dato inválido", "Complete todos los campos con valores válidos.")
                return
            ok, msg = self.bd.alta_producto(cod, nom, pre, stk, self.usuario_actual["username"])
            if ok:
                refrescar_tabla()
                limpiar_campos()
                messagebox.showinfo("Éxito", msg)
            else:
                messagebox.showerror("Error", msg)

        def modificar_producto():
            cod = e_codigo.get().strip().upper()
            try:
                stk = int(e_stock.get().strip())
                if stk < 0:
                    raise ValueError()
                if es_admin:
                    nom = e_nombre.get().strip()
                    pre = float(e_precio.get().strip())
                    if not nom or pre < 0:
                        raise ValueError()
                    ok, msg = self.bd.modificar_producto(cod, stk, self.usuario_actual["username"], nom, pre)
                else:
                    ok, msg = self.bd.modificar_producto(cod, stk, self.usuario_actual["username"])
            except ValueError:
                messagebox.showerror("Dato inválido", "Revise nombre, precio (>=0) y stock (>=0).")
                return

            if ok:
                refrescar_tabla()
                messagebox.showinfo("Éxito", msg)
            else:
                messagebox.showerror("Error", msg)

        def baja_producto():
            if not es_admin:
                messagebox.showwarning("Permiso restringido", "Solo el Administrador puede dar de baja.")
                return
            cod = e_codigo.get().strip().upper()
            if not cod:
                messagebox.showwarning("Código requerido", "Seleccione o ingrese un código.")
                return
            if messagebox.askyesno("Confirmar baja", f"¿Eliminar el producto '{cod}' de la base SQL?"):
                ok, msg = self.bd.baja_producto(cod, self.usuario_actual["username"])
                if ok:
                    refrescar_tabla()
                    limpiar_campos()
                    messagebox.showinfo("Éxito", msg)
                else:
                    messagebox.showerror("Error", msg)

        zona_botones = tk.Frame(panel_der, bg=self.BG_PANEL)
        zona_botones.pack(fill="x", pady=(18, 0))

        if es_admin:
            self._btn_recto(zona_botones, "ALTA PRODUCTO", alta_producto).pack(fill="x", pady=(0, 6))
            self._btn_recto(zona_botones, "MODIFICAR", modificar_producto).pack(fill="x", pady=(0, 6))
            self._btn_recto(zona_botones, "BAJA PRODUCTO", baja_producto, bg="#7F1D1D").pack(fill="x", pady=(0, 6))
        else:
            self._btn_recto(zona_botones, "GUARDAR STOCK", modificar_producto).pack(fill="x", pady=(0, 6))

        self._btn_recto(zona_botones, "LIMPIAR CAMPOS", limpiar_campos, bg="#4B5563").pack(fill="x")
        refrescar_tabla()

    def _construir_vista_cajero(self, parent):
        self.carrito = []
        catalogo_cache = {}

        col_izq = tk.Frame(
            parent,
            bg=self.BG_PANEL,
            highlightbackground=self.BORDE,
            highlightthickness=1,
            padx=14,
            pady=14,
        )
        col_izq.pack(side="left", expand=True, fill="both", padx=(0, 8))

        tk.Label(
            col_izq,
            text="CATÁLOGO DISPONIBLE (SQL)",
            bg=self.BG_ACENTO,
            fg=self.FG_CLARO,
            font=("Segoe UI", 10, "bold"),
            padx=10,
            pady=6,
            anchor="w",
        ).pack(fill="x", pady=(0, 10))

        cols_cat = ("codigo", "nombre", "precio", "stock")
        tabla_cat = ttk.Treeview(col_izq, columns=cols_cat, show="headings", style="Recto.Treeview", height=12)
        tabla_cat.heading("codigo", text="CÓDIGO")
        tabla_cat.heading("nombre", text="PRODUCTO")
        tabla_cat.heading("precio", text="PRECIO")
        tabla_cat.heading("stock", text="STOCK")
        tabla_cat.column("codigo", width=85, anchor="center")
        tabla_cat.column("nombre", width=210, anchor="w")
        tabla_cat.column("precio", width=95, anchor="e")
        tabla_cat.column("stock", width=75, anchor="center")
        tabla_cat.pack(expand=True, fill="both")

        barra_agregar = tk.Frame(col_izq, bg=self.BG_PANEL, pady=10)
        barra_agregar.pack(fill="x")

        tk.Label(
            barra_agregar,
            text="CANTIDAD:",
            bg=self.BG_PANEL,
            fg=self.FG_TEXTO,
            font=("Segoe UI", 9, "bold"),
        ).pack(side="left", padx=(0, 6))

        entry_cant = self._entrada_recta(barra_agregar, width=8)
        entry_cant.insert(0, "1")
        entry_cant.pack(side="left", padx=(0, 10), ipady=3)

        col_der = tk.Frame(
            parent,
            bg=self.BG_PANEL,
            highlightbackground=self.BORDE,
            highlightthickness=1,
            width=430,
            padx=14,
            pady=14,
        )
        col_der.pack(side="right", fill="y", padx=(8, 0))
        col_der.pack_propagate(False)

        tk.Label(
            col_der,
            text="CAJA REGISTRADORA // VENTA ACTUAL",
            bg=self.BG_ACENTO,
            fg=self.FG_CLARO,
            font=("Segoe UI", 10, "bold"),
            padx=10,
            pady=6,
            anchor="w",
        ).pack(fill="x", pady=(0, 10))

        cols_car = ("producto", "cant", "subtotal")
        tabla_car = ttk.Treeview(col_der, columns=cols_car, show="headings", style="Recto.Treeview", height=8)
        tabla_car.heading("producto", text="PRODUCTO")
        tabla_car.heading("cant", text="CANT.")
        tabla_car.heading("subtotal", text="SUBTOTAL")
        tabla_car.column("producto", width=190, anchor="w")
        tabla_car.column("cant", width=65, anchor="center")
        tabla_car.column("subtotal", width=110, anchor="e")
        tabla_car.pack(fill="x")

        lbl_subtotal = tk.Label(
            col_der,
            text="SUBTOTAL: $0.00",
            bg=self.BG_PRINCIPAL,
            fg=self.FG_TEXTO,
            font=("Consolas", 11, "bold"),
            padx=10,
            pady=6,
            anchor="e",
        )
        lbl_subtotal.pack(fill="x", pady=(8, 10))

        marco_pago = tk.Frame(
            col_der,
            bg=self.BG_PRINCIPAL,
            highlightbackground=self.BORDE,
            highlightthickness=1,
            padx=10,
            pady=10,
        )
        marco_pago.pack(fill="x")

        tk.Label(
            marco_pago,
            text="MEDIO DE PAGO",
            bg=self.BG_PRINCIPAL,
            fg=self.FG_TEXTO,
            font=("Segoe UI", 9, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(0, 6))

        medio_var = tk.StringVar(value="Efectivo")
        fila_radios = tk.Frame(marco_pago, bg=self.BG_PRINCIPAL)
        fila_radios.pack(fill="x")

        for texto_mp in ("Efectivo", "Débito", "Crédito"):
            tk.Radiobutton(
                fila_radios,
                text=texto_mp,
                variable=medio_var,
                value=texto_mp,
                bg=self.BG_PRINCIPAL,
                fg=self.FG_TEXTO,
                selectcolor="#FFFFFF",
                activebackground=self.BG_PRINCIPAL,
                font=("Segoe UI", 9, "bold"),
            ).pack(side="left", padx=(0, 12))

        tk.Label(
            marco_pago,
            text="MONTO RECIBIDO (SOLO EFECTIVO):",
            bg=self.BG_PRINCIPAL,
            fg=self.FG_TEXTO,
            font=("Segoe UI", 8, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(8, 2))
        entry_efectivo = self._entrada_recta(marco_pago, width=20)
        entry_efectivo.pack(fill="x", ipady=2)

        lbl_total = tk.Label(
            col_der,
            text="TOTAL A COBRAR: $0.00",
            bg=self.BG_HEADER,
            fg=self.FG_CLARO,
            font=("Consolas", 12, "bold"),
            padx=10,
            pady=8,
            anchor="e",
        )
        lbl_total.pack(fill="x", pady=(10, 10))

        def calcular_subtotal():
            return sum(item["precio"] * item["cantidad"] for item in self.carrito)

        def calcular_total_con_medio(subtotal):
            return subtotal * 1.10 if medio_var.get() == "Crédito" else subtotal

        def actualizar_totales(*args):
            sub = calcular_subtotal()
            tot = calcular_total_con_medio(sub)
            lbl_subtotal.config(text=f"SUBTOTAL: ${sub:.2f}")
            extra = " (+10%)" if medio_var.get() == "Crédito" and sub > 0 else ""
            lbl_total.config(text=f"TOTAL A COBRAR{extra}: ${tot:.2f}")

        medio_var.trace_add("write", actualizar_totales)

        def refrescar_todo():
            catalogo_cache.clear()
            for fila in tabla_cat.get_children():
                tabla_cat.delete(fila)
            for p in self.bd.obtener_productos():
                catalogo_cache[p["codigo"]] = p
                tabla_cat.insert("", "end", values=(p["codigo"], p["nombre"], f"{p['precio']:.2f}", p["stock"]))

            for fila in tabla_car.get_children():
                tabla_car.delete(fila)
            for item in self.carrito:
                sub_item = item["precio"] * item["cantidad"]
                tabla_car.insert("", "end", values=(item["nombre"], item["cantidad"], f"{sub_item:.2f}"))
            actualizar_totales()

        def agregar_al_carrito():
            sel = tabla_cat.selection()
            if not sel:
                messagebox.showwarning("Selección requerida", "Seleccione un producto del catálogo.")
                return
            codigo = tabla_cat.item(sel[0], "values")[0]
            prod = catalogo_cache.get(codigo)
            if not prod:
                return
            try:
                cant = int(entry_cant.get().strip())
                if cant <= 0:
                    raise ValueError()
            except ValueError:
                messagebox.showerror("Cantidad inválida", "Ingrese un entero mayor a 0.")
                return

            en_carrito = sum(x["cantidad"] for x in self.carrito if x["codigo"] == codigo)
            if en_carrito + cant > prod["stock"]:
                messagebox.showerror(
                    "Stock insuficiente",
                    f"Stock disponible de '{prod['nombre']}': {prod['stock']}.",
                )
                return

            for item in self.carrito:
                if item["codigo"] == codigo:
                    item["cantidad"] += cant
                    refrescar_todo()
                    return

            self.carrito.append(
                {
                    "codigo": prod["codigo"],
                    "nombre": prod["nombre"],
                    "precio": prod["precio"],
                    "cantidad": cant,
                }
            )
            refrescar_todo()

        def limpiar_venta():
            self.carrito = []
            entry_efectivo.delete(0, "end")
            refrescar_todo()

        def confirmar_venta():
            if not self.carrito:
                messagebox.showwarning("Carrito vacío", "Agregue productos a la venta.")
                return

            sub = calcular_subtotal()
            medio = medio_var.get()
            tot = calcular_total_con_medio(sub)
            vuelto = 0.0

            if medio == "Efectivo":
                try:
                    abonado = float(entry_efectivo.get().strip())
                except ValueError:
                    messagebox.showerror("Monto inválido", "Ingrese el monto en efectivo.")
                    return
                if abonado < tot:
                    messagebox.showerror("Pago insuficiente", f"Faltan ${(tot - abonado):.2f}.")
                    return
                vuelto = abonado - tot

            ok, msg = self.bd.registrar_venta(
                self.usuario_actual["username"],
                medio,
                self.carrito,
                sub,
                tot,
            )
            if ok:
                extra_msg = f"\nVuelto: ${vuelto:.2f}" if medio == "Efectivo" else "\nPago electrónico aprobado."
                messagebox.showinfo("Venta registrada", f"{msg}\nTotal: ${tot:.2f}{extra_msg}")
                limpiar_venta()
            else:
                messagebox.showerror("Error en venta", msg)
                refrescar_todo()

        self._btn_recto(barra_agregar, "AGREGAR A VENTA", agregar_al_carrito).pack(side="left")

        fila_acciones = tk.Frame(col_der, bg=self.BG_PANEL)
        fila_acciones.pack(fill="x", side="bottom")

        self._btn_recto(fila_acciones, "CANCELAR", limpiar_venta, bg="#7F1D1D").pack(
            side="left", expand=True, fill="x", padx=(0, 4)
        )
        self._btn_recto(fila_acciones, "COBRAR VENTA", confirmar_venta, bg="#14532D").pack(
            side="right", expand=True, fill="x", padx=(4, 0)
        )

        refrescar_todo()


if __name__ == "__main__":
    base = BaseDatosLocal(DB_PATH, SCHEMA_PATH)
    ventana = tk.Tk()
    app = SupermercadoApp(ventana, base)
    ventana.mainloop()