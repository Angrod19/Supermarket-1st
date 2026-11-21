PRAGMA foreign_keys = ON;

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

-- Productos iniciales de ejemplo
INSERT OR IGNORE INTO productos (codigo, nombre, precio, stock) VALUES
    ('P001', 'Leche 1L', 1200.00, 50),
    ('P002', 'Pan Lactal', 1500.00, 30),
    ('P003', 'Arroz 1kg', 950.00, 40),
    ('P004', 'Aceite Girasol 900ml', 2100.00, 25);