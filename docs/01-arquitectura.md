# Arquitectura y estructura del addon

## Identificación

| Elemento | Valor |
|---|---|
| Nombre técnico | `indoor_inventario` |
| Nombre visible | Indoor Inventario |
| Versión | `18.0.6.0.0` |
| Categoría | Inventario |
| Licencia | LGPL-3 |
| Versión objetivo | Odoo 18 Community/Enterprise |

El módulo no reemplaza los motores de compras, stock, valoración o contabilidad de Odoo. Añade procesos de negocio y delega las operaciones contables y de inventario en las API estándar siempre que existe una API adecuada.

## Capas

| Capa | Responsabilidad | Directorios principales |
|---|---|---|
| Modelo | Reglas de negocio, estados, cálculos y validaciones | `models/` |
| Presentación | Formularios, listas, búsquedas, menús y acciones | `views/` |
| Datos | Secuencias, cron, producto marcador y configuración operativa | `data/` |
| Seguridad | Grupos, ACL y reglas multicompañía | `security/` |
| Web | Controladores HTTP, extensiones OWL y estilos | `controllers/`, `static/src/` |
| Reportes | Plantillas QWeb y formato de etiquetas | `report/` |
| Calidad | Casos automatizados de negocio | `tests/` |

## Modelos propios

| Modelo | Tabla | Propósito |
|---|---|---|
| `indoor.standard.cost.batch` | `indoor_standard_cost_batch` | Cabecera del cierre de costos estándar |
| `indoor.standard.cost.line` | `indoor_standard_cost_line` | Resultado y trazabilidad por producto |
| `indoor.provisional.product` | `indoor_provisional_product` | Maestro temporal para productos aún no definitivos |
| `indoor.inventory.count.session` | `indoor_inventory_count_session` | Cabecera de una toma de inventario |
| `indoor.inventory.count.line` | `indoor_inventory_count_line` | Lecturas de productos, cantidades y lotes |
| `indoor.inventory.count.consolidated` | vista SQL | Consolidación de lecturas frente a existencias actuales |

## Modelos estándar extendidos

- `product.template` y `product.product`: política mensual, resumen de costos e inmovilización.
- `purchase.order` y `purchase.order.line`: conversión de productos provisionales y costo inicial.
- `sale.order` y `sale.order.line`: uso y conversión de productos provisionales.
- `stock.picking` y `stock.move`: navegación a la OC, precio de compra y factura por línea.
- `stock.location`, `stock.picking.type` y `stock.warehouse`: entrega a producción.
- `res.config.settings`: parámetros de costos e inmovilización.
- `product.label.layout` e `ir.actions.report`: etiquetas configurables.
- `ir.module.module`: sincronización del nombre visible del módulo.

## Carga del módulo

`__init__.py` importa `models` y `controllers`. `models/__init__.py` importa explícitamente cada archivo de modelo. El orden del arreglo `data` del manifiesto es relevante: seguridad y datos base se cargan antes que las vistas y los menús.

Los activos backend se incorporan a `web.assets_backend`:

- `standard_cost_batch.scss` limita el cambio de disposición al formulario del cierre;
- `protected_form_mode.js` y `protected_form_mode.xml` controlan el modo lectura/edición;
- `barcode_auto_tab_field.js` optimiza la captura por escáner;
- `inventory_count.scss` adapta el conteo a dispositivos móviles.

## Principios de diseño

1. Usar ORM y métodos estándar de Odoo para escrituras de negocio.
2. Mantener los documentos históricos de compra, venta y stock sin modificaciones retroactivas.
3. Aislar compañía, moneda y permisos en los procesos sensibles.
4. Hacer idempotente la preparación de ubicaciones y tipos de operación.
5. Mantener la trazabilidad mediante relaciones, estados, responsables y chatter.
6. Reservar SQL directo para la vista consolidada y la migración técnica de datos heredados.

## Puntos de extensión

- Nuevas reglas del cierre: `IndoorStandardCostBatch.action_calculate()`.
- Nuevas fuentes de precio: `_prepare_purchase_candidates()` y `_purchase_values()`.
- Conversión provisional: `IndoorProvisionalProduct._conversion_values()`.
- Preparación de producción: `StockLocation._setup_indoor_production_delivery()`.
- Consolidación de inventario: `InventoryCountConsolidated.init()`.
- Formatos de etiquetas: `ProductLabelLayout._prepare_report_data()`.

Las extensiones deben preservar los estados, las restricciones SQL, el contexto de compañía y la atomicidad de las operaciones existentes.
