# Entrega a producción y productos inmovilizados

## Objetivo

Registrar consumos de materiales antes de implementar Manufactura y detectar productos sin consumo durante un período configurable.

## Estructura operativa

`StockLocation._setup_indoor_production_delivery()` prepara, por cada almacén:

```text
Ubicaciones virtuales
└── Producción                         usage = view
    └── Consumo materiales             usage = production

Tipo de operación: Entrega a Producción
Origen por defecto:  <almacén>/Stock
Destino por defecto: Producción/Consumo materiales
Código:              internal
Secuencia:           PROD
```

La ubicación destino usa `usage = production`; por eso una transferencia terminada desde una ubicación interna sale del stock disponible y de la valoración de bodega conforme al comportamiento estándar de Odoo.

## Identificadores técnicos

- `stock.location.indoor_is_production_root`: identifica la raíz de producción.
- `stock.location.indoor_is_material_consumption`: identifica el destino de consumo.
- `stock.picking.type.indoor_is_production_delivery`: identifica el tipo de operación.

La preparación reutiliza registros compatibles por nombre y compañía antes de crear otros. No elimina ubicaciones ni tipos de operación existentes y puede ejecutarse repetidamente.

El XML `data/production_consumption_data.xml` ejecuta la preparación al instalar o actualizar. La extensión de `stock.warehouse.create()` la ejecuta para almacenes creados posteriormente.

## Criterio de inmovilización

Para cada `product.template` almacenable se busca el último `stock.move` que cumpla:

- estado `done`;
- origen descendiente de alguna ubicación principal de stock de almacén;
- destino descendiente de una ubicación marcada como consumo de materiales.

La fecha máxima se calcula mediante `_read_group`, agrupando por variante y consolidando el resultado a nivel de plantilla.

```text
fecha límite = ahora - meses configurados
inmovilizado = existe último consumo y último consumo < fecha límite
```

Un producto sin consumo registrado no se marca automáticamente como inmovilizado. Si un producto inmovilizado recibe un consumo reciente, la marca se retira en la siguiente actualización.

## Campos de producto

| Campo | Modelo | Descripción |
|---|---|---|
| `indoor_is_immobilized` | `product.template` | Marca automática, almacenada e indexada |
| `indoor_last_consumption_date` | `product.template` | Último consumo detectado |
| mismos nombres relacionados | `product.product` | Exposición por variante |

Ambos campos son de sólo lectura para evitar clasificaciones manuales que contradigan el cálculo.

## Configuración y ejecución

El parámetro `indoor_inventario.immobilization_months` tiene valor inicial 6 y un mínimo validado de 1.

En **Inventario > Configuración > Ajustes > Control de productos inmovilizados** se puede:

- cambiar los meses sin consumo;
- ejecutar **Actualizar ahora**;
- recibir un resumen de productos evaluados, inmovilizados, marcados y liberados.

## Acción programada

`ir_cron_update_immobilized_products` se ejecuta diariamente. `_schedule_immobilized_products_cron()` calcula la siguiente ejecución a las 03:00 en la zona horaria de la compañía; usa como respaldo la zona de un usuario de la compañía y finalmente UTC.

El cron vuelve a programar su siguiente ejecución después de procesar, lo que conserva las 03:00 locales frente a cambios de huso horario.

## Consideraciones

- Sólo los movimientos hacia la ubicación marcada cuentan como consumo.
- Transferencias internas a otras sububicaciones no inmovilizan ni liberan productos.
- La marca representa falta de consumo productivo, no falta de cualquier movimiento logístico.
- Si se cambia manualmente la estructura de ubicaciones, se deben preservar las marcas técnicas o ejecutar nuevamente la preparación.
