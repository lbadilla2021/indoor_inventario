# Actualización mensual de costos estándar

## Objetivo

Calcular una propuesta mensual de costo estándar usando hasta las tres compras más recientes efectivamente recibidas, permitir su revisión y aprobación y aplicar el costo mediante `product.product.standard_price`.

## Modelos

### `indoor.standard.cost.batch`

Cabecera del proceso. Sus estados son:

```text
Borrador -> Calculado -> Aprobado -> Aplicado
     |           |
     +-----------+----> Cancelado
```

Registra compañía, fecha de cierre, responsables, fechas de cada etapa, parámetros copiados desde configuración, totales y chatter. La secuencia `indoor.standard.cost.batch` genera referencias `CST/<año>/<correlativo>`.

Un cierre aplicado es inmutable. La restricción `unique_applied_closing` impide dos cierres aplicados para la misma compañía y fecha.

### `indoor.standard.cost.line`

Conserva por producto:

- stock y costo anterior;
- cantidad y valor de compras consideradas;
- costo calculado y costo aprobado;
- diferencias absoluta, porcentual y de inventario;
- estado de validación y nivel de advertencia;
- OC, línea de OC, proveedor, fecha, cantidad, precio y recepciones de cada una de las tres posiciones.

La restricción `unique_product_batch` evita duplicar un producto dentro del mismo cierre.

## Selección de productos

`action_calculate()` busca variantes que cumplan simultáneamente:

- `use_monthly_standard_cost = True`;
- `is_storable = True`.

El botón **Incluir productos elegibles** activa la política en plantillas almacenables con método de costo estándar. La acción sólo está disponible en borrador y es explícita para evitar incorporar productos de manera silenciosa.

## Selección de compras

`_prepare_purchase_candidates()` consulta movimientos `stock.move` que:

- pertenecen a la compañía del cierre;
- corresponden a los productos participantes;
- tienen `purchase_line_id`;
- provienen de órdenes confirmadas o terminadas;
- están en estado `done`;
- ocurrieron hasta el final del día de cierre.

La unidad lógica es `purchase.order.line`. Todas sus recepciones parciales se agregan antes de ordenar las compras. Las devoluciones reembolsables restan cantidad según la semántica de Odoo 18. Líneas con cantidad neta no positiva quedan fuera.

El precio base se obtiene con `_get_gross_price_unit()`, se convierte a la moneda de la compañía mediante `res.currency._convert(..., round=False)` usando la fecha real de recepción y se expresa en la UoM base del producto.

## Fórmula

Para las `n` compras disponibles, con `1 <= n <= 3`:

```text
PPM = SUM(cantidad recibida normalizada × precio convertido)
      -------------------------------------------------------
               SUM(cantidad recibida normalizada)
```

Si no existen compras, se mantiene el costo anterior y la línea queda en estado `no_purchase`. Nunca se propone cero únicamente por falta de compras.

## Stock histórico y valorización

El stock se consulta con contexto `to_date` al final del día de cierre:

```text
Inventario anterior   = stock de cierre × costo anterior
Nuevo inventario      = stock de cierre × costo aprobado
Diferencia inventario = nuevo inventario - inventario anterior
```

La aplicación escribe `standard_price` por ORM y deja que `stock_account` ejecute la revalorización nativa. El resultado contable depende del método de valoración, cuentas, diario y permisos configurados en Odoo.

## Validaciones

| Estado | Condición |
|---|---|
| `ready` | Producto apto y con compras utilizables |
| `no_purchase` | No existen compras utilizables |
| `stale` | La compra más reciente supera la antigüedad configurada |
| `invalid_method` | La categoría no usa costo estándar |
| `negative_stock` | El stock histórico es negativo |

El stock negativo bloquea el lote completo. Las líneas con método inválido no se aplican. Una diferencia superior al umbral de advertencia o crítico define `warning_level` y las decoraciones de la grilla.

## Aprobación y aplicación

- El analista calcula, recalcula y revisa.
- El aprobador puede modificar `approved_standard_price` mientras el batch está calculado.
- La línea registra `approved_changed_by` y `approved_changed_at` al modificar el aprobado.
- Sólo el grupo `group_standard_cost_approver` puede aprobar y aplicar.
- No hay commits manuales; una excepción revierte la transacción completa.

Al aplicar se actualizan los campos resumen dependientes de compañía en `product.product` y se publica en el chatter un resumen de productos y valores.

## Interfaz y reportes

- Menú: **Inventario > Operaciones > Actualización de Costos Estándar**.
- Historial: lista, formulario y tabla dinámica en reportes.
- Diagnóstico: productos bajo política mensual cuyo método no es estándar.
- Exportación: `action_export_xlsx()` entrega la grilla mediante la ruta autenticada `/indoor_inventario/standard_cost_batch/<id>/xlsx`.
- Disposición: la clase `o_indoor_cost_batch_form` y su SCSS colocan el chatter bajo el formulario y mantienen el ancho completo.

## Parámetros

| Clave técnica | Valor inicial | Uso |
|---|---:|---|
| `indoor_costos_estandar.purchase_count` | 3 | Número de compras, limitado entre 1 y 3 |
| `indoor_costos_estandar.stale_days` | 180 | Antigüedad para marcar compra obsoleta |
| `indoor_costos_estandar.warning_threshold` | 10 | Umbral porcentual de advertencia |
| `indoor_costos_estandar.critical_threshold` | 20 | Umbral porcentual crítico |

Cada cierre copia estos parámetros al calcular, conservando el criterio histórico aunque la configuración cambie después.

## Limitaciones deliberadas

- No cambia categorías AVCO/FIFO a estándar.
- No modifica compras, facturas o movimientos históricos.
- No admite más de tres posiciones de compra en la tabla de auditoría.
- No crea manualmente SVL ni asientos contables.
- La tasa de cambio y la configuración contable deben existir en Odoo.
