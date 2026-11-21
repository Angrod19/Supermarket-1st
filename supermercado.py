import tkinter as tk
from tkinter import ttk, messagebox


class Usuario:
    def __init__(self, username: str, password: str, rol: str):
        self.username = username
        self.password = password
        self.rol = rol  # "administrador", "supervisor", "cajero"


class Producto:
    def __init__(self, codigo: str, nombre: str, precio: float, stock: int):
        self.codigo = codigo
        self.nombre = nombre
        self.precio = float(precio)
        self.stock = int(stock)


class SupermercadoApp:
    # Paleta sobria y geométrica de bordes rectos
    BG_PRINCIPAL = "#E6E8EB"
    BG_PANEL = "#FFFFFF"
    BG_HEADER = "#1F2933"
    BG_ACENTO = "#2B3A4A"
    FG_CLARO = "#FFFFFF"
    FG_TEXTO = "#111827"
    BORDE = "#9CA3AF"

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("SISTEMA DE SUPERMERCADO - TERMINAL LOCAL")
        self.root.geometry("1040x680")
        self.root.minsize(920, 600)
        self.root.configure(bg=self.BG_PRINCIPAL)

        self.usuarios = {
            "admin": Usuario("admin", "1234", "administrador"),
            "super": Usuario("super", "1234", "supervisor"),
            "cajero1": Usuario("cajero1", "1234", "cajero"),
        }

        self.inventario = {
            "P001": Producto("P001", "Leche 1L", 1200.00, 50),
            "P002": Producto("P002", "Pan Lactal", 1500.00, 30),
            "P003": Producto("P003", "Arroz 1kg", 950.00, 40),
            "P004": Producto("P004", "Aceite Girasol 900ml", 2100.00, 25),
        }

        self.usuario_actual = None
        self.carrito = []  # Lista de dicts: {"producto": Producto, "cantidad": int}

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
        style.map(
            "Recto.Treeview.Heading",
            background=[("active", self.BG_HEADER)],
        )

    def _limpiar_ventana(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def _btn_recto(self, parent, texto, comando, bg=BG_ACENTO, fg=FG_CLARO, width=None):
        kwargs = {
            "text": texto,
            "command": comando,
            "bg": bg,
            "fg": fg,
            "activebackground": self.BG_HEADER,
            "activeforeground": self.FG_CLARO,
            "relief": "flat",
            "bd": 0,
            "highlightthickness": 1,
            "highlightbackground": self.BG_HEADER,
            "font": ("Segoe UI", 10, "bold"),
            "cursor": "hand2",
            "padx": 14,
            "pady": 7,
        }
        if width is not None:
            kwargs["width"] = width
        return tk.Button(parent, **kwargs)

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

    # ==========================================================
    # PANTALLA DE INICIO DE SESIÓN (ESTRUCTURA CUADRADA)
    # ==========================================================
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
            pady=32,
        )
        caja_login.place(relx=0.5, rely=0.5, anchor="center")

        cabecera = tk.Frame(caja_login, bg=self.BG_HEADER, padx=16, pady=12)
        cabecera.pack(fill="x", pady=(0, 22))
        tk.Label(
            cabecera,
            text="SUPERMERCADO // ACCESO AL SISTEMA",
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
        entry_user = self._entrada_recta(caja_login, width=32)
        entry_user.pack(fill="x", pady=(4, 14), ipady=4)
        entry_user.focus_set()

        tk.Label(
            caja_login,
            text="CONTRASEÑA",
            bg=self.BG_PANEL,
            fg=self.FG_TEXTO,
            font=("Segoe UI", 9, "bold"),
            anchor="w",
        ).pack(fill="x")
        entry_pass = self._entrada_recta(caja_login, show="*", width=32)
        entry_pass.pack(fill="x", pady=(4, 20), ipady=4)

        def intentar_login(event=None):
            u = entry_user.get().strip()
            p = entry_pass.get().strip()
            if u in self.usuarios and self.usuarios[u].password == p:
                self.usuario_actual = self.usuarios[u]
                self.mostrar_panel_principal()
            else:
                messagebox.showerror("Acceso denegado", "Usuario o contraseña incorrectos.")

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
        ayuda.pack(fill="x", pady=(20, 0))
        tk.Label(
            ayuda,
            text=(
                "Cuentas de prueba (clave: 1234)\n"
                "• admin   -> Administrador (Alta/Baja/Modificación)\n"
                "• super   -> Supervisor (Modificación de stock)\n"
                "• cajero1 -> Cajero (Caja registradora y ventas)"
            ),
            bg=self.BG_PRINCIPAL,
            fg=self.FG_TEXTO,
            font=("Consolas", 9),
            justify="left",
            anchor="w",
        ).pack(fill="x")

    # ==========================================================
    # PANEL PRINCIPAL SEGÚN ROL
    # ==========================================================
    def mostrar_panel_principal(self):
        self._limpiar_ventana()
        rol = self.usuario_actual.rol

        # Barra superior cuadrada
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
            text=f"TERMINAL LOCAL  |  USUARIO: {self.usuario_actual.username.upper()}  |  ROL: {rol.upper()}",
            bg=self.BG_HEADER,
            fg=self.FG_CLARO,
            font=("Segoe UI", 11, "bold"),
        ).pack(side="left")

        self._btn_recto(
            barra_top,
            "CERRAR SESIÓN",
            self.mostrar_pantalla_login,
            bg="#7F1D1D",
        ).pack(side="right")

        # Contenedor principal dividido en módulos cuadrados
        cuerpo = tk.Frame(self.root, bg=self.BG_PRINCIPAL, padx=16, pady=16)
        cuerpo.pack(expand=True, fill="both")

        if rol == "administrador":
            self._construir_vista_admin_o_supervisor(cuerpo, es_admin=True)
        elif rol == "supervisor":
            self._construir_vista_admin_o_supervisor(cuerpo, es_admin=False)
        elif rol == "cajero":
            self._construir_vista_cajero(cuerpo)

    # ==========================================================
    # VISTA ADMINISTRADOR / SUPERVISOR
    # ==========================================================
    def _construir_vista_admin_o_supervisor(self, parent, es_admin: bool):
        # Panel izquierdo: Stock General
        panel_izq = tk.Frame(
            parent,
            bg=self.BG_PANEL,
            highlightbackground=self.BORDE,
            highlightthickness=1,
            padx=14,
            pady=14,
        )
        panel_izq.pack(side="left", expand=True, fill="both", padx=(0, 8))

        titulo_izq = "STOCK GENERAL (ADMINISTRACIÓN)" if es_admin else "STOCK GENERAL (SUPERVISIÓN)"
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

        # Panel derecho: Formulario de operaciones cuadradas
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
            for p in self.inventario.values():
                tabla.insert("", "end", values=(p.codigo, p.nombre, f"{p.precio:.2f}", p.stock))

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
            prod = self.inventario.get(vals[0])
            if not prod:
                return
            e_codigo.configure(state="normal")
            e_codigo.delete(0, "end")
            e_codigo.insert(0, prod.codigo)
            if es_admin:
                e_codigo.configure(state="readonly")
                e_nombre.delete(0, "end")
                e_nombre.insert(0, prod.nombre)
                e_precio.delete(0, "end")
                e_precio.insert(0, f"{prod.precio:.2f}")
            e_stock.delete(0, "end")
            e_stock.insert(0, str(prod.stock))

        tabla.bind("<<TreeviewSelect>>", al_seleccionar)

        def alta_producto():
            if not es_admin:
                messagebox.showwarning("Permiso restringido", "Solo el Administrador puede dar de alta productos.")
                return
            cod = e_codigo.get().strip().upper()
            nom = e_nombre.get().strip()
            try:
                pre = float(e_precio.get().strip())
                stk = int(e_stock.get().strip())
            except ValueError:
                messagebox.showerror("Dato inválido", "Precio debe ser numérico y stock un entero.")
                return
            if not cod or not nom or pre < 0 or stk < 0:
                messagebox.showerror("Dato inválido", "Complete código, nombre y valores no negativos.")
                return
            if cod in self.inventario:
                messagebox.showerror("Duplicado", f"Ya existe un producto con código {cod}.")
                return
            self.inventario[cod] = Producto(cod, nom, pre, stk)
            refrescar_tabla()
            limpiar_campos()
            messagebox.showinfo("Alta exitosa", f"Producto '{nom}' agregado al stock.")

        def modificar_producto():
            cod = e_codigo.get().strip().upper()
            if cod not in self.inventario:
                messagebox.showerror("No encontrado", "Seleccione o ingrese un código de producto existente.")
                return
            prod = self.inventario[cod]
            try:
                stk = int(e_stock.get().strip())
                if stk < 0:
                    raise ValueError()
                if es_admin:
                    nom = e_nombre.get().strip()
                    pre = float(e_precio.get().strip())
                    if not nom or pre < 0:
                        raise ValueError()
                    prod.nombre = nom
                    prod.precio = pre
                prod.stock = stk
            except ValueError:
                messagebox.showerror("Dato inválido", "Revise nombre, precio (>=0) y stock entero (>=0).")
                return
            refrescar_tabla()
            messagebox.showinfo("Actualizado", f"Datos de '{prod.nombre}' guardados.")

        def baja_producto():
            if not es_admin:
                messagebox.showwarning("Permiso restringido", "Solo el Administrador puede dar de baja productos.")
                return
            cod = e_codigo.get().strip().upper()
            if cod not in self.inventario:
                messagebox.showerror("No encontrado", "Seleccione o ingrese un código válido para dar de baja.")
                return
            prod = self.inventario[cod]
            if messagebox.askyesno("Confirmar baja", f"¿Eliminar '{prod.nombre}' ({cod}) del stock general?"):
                del self.inventario[cod]
                refrescar_tabla()
                limpiar_campos()

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

    # ==========================================================
    # VISTA CAJERO (CAJA REGISTRADORA)
    # ==========================================================
    def _construir_vista_cajero(self, parent):
        self.carrito = []

        # Columna izquierda: Catálogo y agregado al carrito
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
            text="CATÁLOGO DISPONIBLE",
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

        # Columna derecha: Ticket / Carrito y Medios de Pago
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

        # Medio de pago cuadrado
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
            return sum(item["producto"].precio * item["cantidad"] for item in self.carrito)

        def calcular_total_con_medio(subtotal):
            if medio_var.get() == "Crédito":
                return subtotal * 1.10
            return subtotal

        def actualizar_totales(*args):
            sub = calcular_subtotal()
            tot = calcular_total_con_medio(sub)
            lbl_subtotal.config(text=f"SUBTOTAL: ${sub:.2f}")
            extra = " (+10%)" if medio_var.get() == "Crédito" and sub > 0 else ""
            lbl_total.config(text=f"TOTAL A COBRAR{extra}: ${tot:.2f}")

        medio_var.trace_add("write", actualizar_totales)

        def refrescar_todo():
            for fila in tabla_cat.get_children():
                tabla_cat.delete(fila)
            for p in self.inventario.values():
                tabla_cat.insert("", "end", values=(p.codigo, p.nombre, f"{p.precio:.2f}", p.stock))

            for fila in tabla_car.get_children():
                tabla_car.delete(fila)
            for item in self.carrito:
                sub_item = item["producto"].precio * item["cantidad"]
                tabla_car.insert(
                    "",
                    "end",
                    values=(item["producto"].nombre, item["cantidad"], f"{sub_item:.2f}"),
                )
            actualizar_totales()

        def agregar_al_carrito():
            sel = tabla_cat.selection()
            if not sel:
                messagebox.showwarning("Selección requerida", "Seleccione un producto del catálogo.")
                return
            codigo = tabla_cat.item(sel[0], "values")[0]
            prod = self.inventario[codigo]
            try:
                cant = int(entry_cant.get().strip())
                if cant <= 0:
                    raise ValueError()
            except ValueError:
                messagebox.showerror("Cantidad inválida", "Ingrese un número entero mayor a 0.")
                return

            en_carrito = sum(x["cantidad"] for x in self.carrito if x["producto"].codigo == codigo)
            if en_carrito + cant > prod.stock:
                messagebox.showerror(
                    "Stock insuficiente",
                    f"Stock disponible de '{prod.nombre}': {prod.stock} (en venta: {en_carrito}).",
                )
                return

            for item in self.carrito:
                if item["producto"].codigo == codigo:
                    item["cantidad"] += cant
                    refrescar_todo()
                    return

            self.carrito.append({"producto": prod, "cantidad": cant})
            refrescar_todo()

        def limpiar_venta():
            self.carrito = []
            entry_efectivo.delete(0, "end")
            refrescar_todo()

        def confirmar_venta():
            if not self.carrito:
                messagebox.showwarning("Carrito vacío", "Agregue al menos un producto a la venta.")
                return

            sub = calcular_subtotal()
            medio = medio_var.get()
            total = calcular_total_con_medio(sub)
            vuelto = 0.0

            if medio == "Efectivo":
                try:
                    abonado = float(entry_efectivo.get().strip())
                except ValueError:
                    messagebox.showerror("Monto inválido", "Ingrese el monto recibido en efectivo.")
                    return
                if abonado < total:
                    messagebox.showerror(
                        "Pago insuficiente",
                        f"Faltan ${(total - abonado):.2f} para cubrir el total.",
                    )
                    return
                vuelto = abonado - total

            # Descontar stock en el inventario general
            for item in self.carrito:
                item["producto"].stock -= item["cantidad"]

            detalle_pago = f"\nVuelto: ${vuelto:.2f}" if medio == "Efectivo" else "\nPago electrónico aprobado."
            messagebox.showinfo(
                "Venta registrada",
                f"Medio de pago: {medio}\nTotal cobrado: ${total:.2f}{detalle_pago}\nStock descontado correctamente.",
            )
            limpiar_venta()

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
    ventana = tk.Tk()
    app = SupermercadoApp(ventana)
    ventana.mainloop()