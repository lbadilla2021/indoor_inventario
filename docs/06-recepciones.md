# Extensiones de recepciones

## Objetivo

Mostrar en una recepción la orden de compra de origen, el precio registrado en la línea de compra y una referencia de factura por línea de movimiento.

## Apertura modal de la orden de compra

`stock.picking.action_open_purchase_order_modal()` obtiene la orden desde `purchase_id`. Como respaldo busca `purchase.order.name == origin` dentro de la misma compañía.

La acción abre `purchase.purchase_order_form` con:

- `target = new`;
- creación, edición y eliminación deshabilitadas;
- modo inicial de sólo lectura.

La vista sustituye el campo `origin` por una fila que conserva el valor y añade el botón de enlace externo. El botón sólo aparece en recepciones con `purchase_id`.

## Campos añadidos a `stock.move`

| Campo | Tipo | Origen/uso |
|---|---|---|
| `purchase_currency_id` | Many2one relacionado | Moneda de `purchase_line_id` |
| `purchase_price_unit` | Float relacionado | `purchase_line_id.price_unit` |
| `vendor_invoice_ref` | Char | Número de factura indicado por el usuario |

El precio mostrado es el precio unitario de la línea de OC en su moneda, no un costo convertido ni un precio recalculado por la recepción.

`vendor_invoice_ref` se almacena por `stock.move`, no por cabecera, por lo que una recepción puede asociar facturas distintas a productos diferentes. El campo queda de sólo lectura cuando el movimiento está terminado o cancelado.

## Vistas afectadas

- Lista `move_ids_without_package` dentro del formulario de `stock.picking`.
- Formulario de operaciones detalladas `stock.view_stock_move_operations`.

Los campos se ocultan para operaciones cuyo `picking_type_code` no sea `incoming`; por lo tanto no alteran visualmente entregas ni transferencias internas.

## Consideraciones funcionales

- El número de factura es una referencia logística; no crea ni vincula automáticamente `account.move`.
- Si se necesita una relación contable formal, debe añadirse un Many2one a la factura y definir reglas de conciliación.
- Una línea de movimiento representa el nivel de detalle soportado actualmente. La división por operaciones detalladas/lotes no genera referencias de factura independientes.
