# Toma de inventario

## Objetivo

Registrar conteos físicos mediante códigos de barras, agrupar lecturas por sesión y preparar ajustes en el inventario físico estándar de Odoo.

La funcionalidad pertenece completamente a `indoor_inventario` y no requiere el addon legado `ziv_cod_barra` después de migrar sus datos.

## Modelos

### `indoor.inventory.count.session`

Cabecera con referencia secuencial, ubicación, compañía, responsable, fechas, lecturas y chatter.

Estados:

```text
Borrador -> En proceso -> En revisión -> Cerrado
    |            |             |
    +------------+-------------+-> Cancelado
```

La secuencia usa el código `indoor.inventory.count.session` y genera referencias `CI/<año>/<correlativo>`.

### `indoor.inventory.count.line`

Cada lectura registra:

- sesión y estado relacionado;
- código de barras y producto almacenable;
- cantidad positiva;
- UoM, compañía y ubicación;
- lote/serie cuando el producto tiene seguimiento;
- usuario, fecha y nota.

Si no se entrega una sesión por contexto, el modelo busca una sesión abierta del usuario o crea una. Al crear la primera línea, una sesión en borrador pasa automáticamente a `in_progress`.

### `indoor.inventory.count.consolidated`

Modelo `_auto = False` respaldado por una vista SQL. Agrupa por sesión, ubicación, producto y lote:

- cantidad contada;
- existencia actual en `stock.quant`;
- diferencia;
- número de lecturas;
- número de usuarios;
- fecha de última lectura.

Se excluyen quants con paquete o propietario porque la sesión no captura esas dimensiones.

## Captura por código de barras

`_onchange_barcode()` busca una coincidencia única en `product.product.barcode`:

- una coincidencia: asigna producto y cantidad inicial;
- varias coincidencias: muestra advertencia de código duplicado;
- ninguna coincidencia: muestra advertencia de producto inexistente.

El widget `indoor_barcode_auto_tab` confirma el código al pulsar Enter/Tab o 450 ms después de la entrada, y mueve el foco al campo de cantidad. El SCSS aumenta el tamaño de los controles en móviles.

## Preparación del inventario físico

Desde una sesión en revisión, un administrador de inventario ejecuta `action_prepare_physical_inventory()`:

1. valida grupo, estado y existencia de lecturas;
2. consulta el consolidado;
3. busca o crea cada `stock.quant` correspondiente;
4. escribe `inventory_quantity`, usuario y fecha en contexto `inventory_mode`;
5. registra quién preparó y cuántas líneas;
6. abre la lista editable de inventario físico con filtro pendiente de aplicar.

El método prepara el ajuste, pero no lo aplica automáticamente. El usuario debe revisar y aplicar las diferencias usando el flujo estándar de Odoo antes de cerrar la sesión.

## Menús y acciones

- **Inventariar**: opción principal bajo Inventario, abre la captura en formulario/lista.
- **Operaciones > Sesiones Inventario**: administración de sesiones.
- **Reportes > Sesiones Inventario**: consolidado agrupado por sesión, sólo para administradores.

## Migración desde `ziv_cod_barra`

La función XML al final de `views/inventory_count_views.xml` ejecuta `_migrate_from_ziv_cod_barra()` durante la actualización.

La migración:

- detecta las tablas heredadas antes de actuar;
- copia sesiones y líneas manteniendo IDs;
- evita duplicados con `ON CONFLICT DO NOTHING`;
- corrige secuencias PostgreSQL;
- conserva el mayor correlativo de secuencia;
- reasigna chatter, seguidores, actividades y adjuntos;
- desactiva el menú raíz legado si todavía existe.

El SQL se limita a esta migración y a la vista consolidada. Antes de desinstalar el addon legado se debe actualizar `indoor_inventario`, verificar sesiones, consolidado y adjuntos y realizar un respaldo de la base.

## Reglas de integridad

- Cantidad estrictamente mayor que cero.
- Lote o serie obligatorio cuando el producto lo exige.
- Lecturas modificables sólo en borrador o en proceso.
- Ubicaciones limitadas a uso interno y compañía compatible.
- Preparación reservada a `stock.group_stock_manager`.
