# Seguridad, multicompañía y auditoría

## Grupos de costos

| Grupo | Herencia | Responsabilidad |
|---|---|---|
| `group_standard_cost_analyst` | Usuario de inventario | Crear, calcular, recalcular y revisar cierres |
| `group_standard_cost_approver` | Analista de costos | Aprobar y aplicar costos |

Los métodos `action_approve()` y `action_apply()` validan el grupo aprobador en servidor, además de ocultar botones por grupo en la vista.

## ACL

### Costos estándar

El analista tiene lectura, escritura, creación y eliminación sobre batches y líneas. La lógica del modelo restringe eliminación y edición según estado; las ACL por sí solas no describen toda la protección.

El aprobador tiene lectura sobre `stock.valuation.layer`, necesaria para revisar la valoración resultante sin permitir modificarla desde este módulo.

### Productos provisionales

Usuarios de ventas, compras e inventario reciben permisos CRUD sobre `indoor.provisional.product`. La regla de compañía restringe los registros visibles.

### Toma de inventario

- Usuario de inventario: lectura, escritura y creación de sesiones/líneas, sin eliminación.
- Administrador de inventario: CRUD completo de sesiones/líneas.
- Consolidado: sólo lectura para usuarios y administradores.

La preparación de quants comprueba explícitamente `stock.group_stock_manager` en servidor.

## Reglas de registro

| Modelo | Dominio |
|---|---|
| `indoor.standard.cost.batch` | `company_id in company_ids` |
| `indoor.standard.cost.line` | `company_id in company_ids` |
| `indoor.provisional.product` | `company_id in company_ids` |

Además, los cálculos y conversiones usan `with_company()` o filtran `company_id` para evitar mezclar costos, monedas, compras y documentos entre compañías.

## Auditoría de costos

El batch hereda `mail.thread` y `mail.activity.mixin`. Se registran como mínimo:

- cálculo y cantidad de productos;
- inclusión masiva de productos elegibles;
- aprobación y usuario;
- aplicación, cantidad actualizada y valores agregados.

Los campos `calculated_by/at`, `approved_by/at` y `applied_by/at` conservan responsables y marcas de tiempo. Las líneas guardan el usuario y la fecha de cambios al costo aprobado y mantienen relaciones navegables hacia las compras y recepciones.

## Inmutabilidad

- `indoor.standard.cost.batch.write()` bloquea cambios funcionales en cierres aplicados.
- `unlink()` impide eliminar cierres aprobados o aplicados.
- Las líneas no se editan después de aprobar, aplicar o cancelar.
- Las líneas aprobadas o aplicadas no se eliminan.
- Una restricción SQL impide aplicaciones duplicadas por compañía/fecha.

## Auditoría de inventario físico

Las sesiones heredan chatter. Cada lectura conserva usuario y fecha. Al preparar el inventario se registran responsable, fecha y número de quants preparados y se publica un mensaje en la sesión.

## Exposición HTTP

La descarga XLSX exige `auth="user"`, verifica que el batch exista y ejecuta `check_access("read")`. Un registro inexistente o no autorizado devuelve `404`, evitando revelar su existencia.

## Riesgos y controles

- El modo de sólo lectura de formularios es UX, no seguridad de servidor.
- Los campos `sudo()` usados en tareas técnicas están limitados a preparación, consulta global o escritura controlada.
- Las rutas y procesos deben probarse con usuarios reales de cada rol, no sólo con administrador.
- Cualquier modelo nuevo con `company_id` debe incorporar regla de registro antes de publicarse.
