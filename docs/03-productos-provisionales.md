# Productos provisionales

## Problema resuelto

Permite cotizar o comprar un artículo todavía no aprobado como producto definitivo sin llenar el maestro de productos con registros que podrían no concretarse.

## Modelo `indoor.provisional.product`

El registro provisional vive en un maestro separado y contiene:

- nombre y descripción;
- compañía y moneda;
- categoría obligatoria;
- tipo `goods` o `service`, con `goods` por defecto;
- UoM de venta y de compra compatibles;
- ruta obligatoria con regla de compra;
- indicadores de venta y compra activados por defecto;
- costo, origen, estado y producto definitivo relacionado;
- vínculos a líneas de venta y compra.

Estados:

```text
Borrador -> Cotizado -> Aprobado -> Convertido
    |           |
    +-----------+-----------------> Descartado -> Borrador
```

Un producto convertido no puede descartarse. La conversión puede vincular un producto existente o crear una nueva plantilla.

## Producto marcador

El dato `product_template_provisional_placeholder` crea un único producto técnico visible como **Producto Provisional**. Se usa en líneas estándar de Odoo mientras el artículo todavía no tiene una variante definitiva.

La función de instalación `_configure_placeholder_product()` mantiene el nombre, la activación y los indicadores de venta/compra. El marcador no reemplaza al maestro provisional: sólo permite que una línea estándar tenga un `product_id` válido.

## Integración con ventas

`sale.order.line` añade:

- `provisional_product_id`;
- `is_provisional_placeholder`.

Al seleccionar un provisional se asignan el marcador, la UoM y la descripción. Al confirmar la venta:

1. se valida que toda línea marcada tenga un provisional;
2. se crea o recupera el producto definitivo;
3. se reemplaza el marcador en la línea;
4. continúa el flujo estándar de confirmación.

## Integración con compras

`purchase.order.line` usa la misma relación y añade la conversión del precio a moneda y UoM de la compañía.

Al confirmar o aprobar la compra:

1. se validan las líneas incompletas;
2. se calcula el costo neto de cada provisional;
3. se convierte moneda con `round=False` y la fecha de la orden;
4. se normaliza a la UoM del provisional;
5. se crea o recupera el producto definitivo;
6. se reemplaza el marcador en la línea de compra;
7. se escribe el costo ponderado en `standard_price` después de la confirmación.

Si el mismo provisional aparece en varias líneas de la orden, el costo inicial se pondera por cantidad.

## Creación del producto definitivo

`_conversion_values()` genera una plantilla con:

- categoría definida en el provisional;
- bien almacenable o servicio según `product_kind`;
- UoM de venta y compra;
- ruta Comprar seleccionada;
- `sale_ok` y `purchase_ok` según el provisional;
- compañía correspondiente.

El costo no es obligatorio antes de la compra. En el flujo de compra se obtiene del precio de la línea confirmada. La conversión manual sin compra puede crear el producto sin costo inicial.

## Multicompañía y validaciones

- El dominio limita provisionales a la compañía de la orden.
- Una regla de registro restringe el maestro a `company_ids`.
- Las UoM deben pertenecer a la misma categoría.
- La ruta debe contener al menos una regla con acción `buy`.
- Las líneas conservan descripción y precio al sustituir el marcador.

## Interfaz

- Menú: **Inventario > Productos > Productos provisionales**.
- En ventas y compras, **Producto** aparece antes de **Producto provisional**.
- La columna provisional sólo se muestra cuando la línea usa el marcador mediante `column_invisible`/condiciones de vista.
- El formulario provisional permite aprobar, convertir, descartar, restaurar y abrir el producto definitivo.
