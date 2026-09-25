# Pruebas y mantenimiento

## Suite automatizada

Los casos usan `odoo.tests.common.TransactionCase` y se distribuyen por temática.

### `tests/test_standard_cost.py`

Incluye 18 casos:

1. tres compras ponderadas;
2. dos compras;
3. una compra;
4. ausencia de compras;
5. recepción parcial;
6. compra cancelada;
7. recepción futura;
8. conversión de UoM;
9. conversión de moneda;
10. aislamiento de compañía;
11. exclusión de AVCO al aplicar;
12. prevención de doble aplicación;
13. creación de SVL nativa;
14. stock cero;
15. bloqueo por stock negativo;
16. devolución a proveedor;
17. costo aprobado distinto del calculado;
18. incorporación masiva explícita.

### Otras suites

| Archivo | Cobertura |
|---|---|
| `test_provisional_product.py` | Conversión desde venta/compra, costo inicial y marcador obligatorio |
| `test_immobilized_product.py` | Preparación idempotente, marcado/liberación, ausencia de consumos y cron 03:00 |
| `test_inventory_count.py` | Sesiones, consolidado, código de barras, menús y reporte de etiquetas |
| `test_receipt_details.py` | Precio de compra, factura por línea y apertura modal |

## Ejecución sugerida

En una base exclusiva para pruebas:

```bash
docker exec odoo bash -lc 'odoo -d BASE_PRUEBAS -u indoor_inventario --test-enable --stop-after-init --workers=0 --db_host="$HOST" --db_user="$USER" --db_password="$PASSWORD"'
```

No ejecute pruebas transaccionales en una base de producción. Algunas pruebas crean almacenes, productos, movimientos, compras, monedas, sesiones y capas de valoración.

## Pruebas manuales mínimas

### Costos

- Comparar el PPM contra un cálculo manual.
- Confirmar orden por última recepción y tratamiento de devoluciones.
- Probar costo aprobado diferente del calculado.
- Verificar bloqueo por stock negativo y AVCO/FIFO.
- Revisar SVL y asiento en valoración automática.

### Productos provisionales

- Confirmar visibilidad condicional de la columna.
- Convertir desde venta y compra.
- Verificar UoM, ruta, indicadores y costo resultante.
- Confirmar separación por compañía.

### Producción e inmovilizados

- Transferir desde stock a Consumo materiales.
- Comprobar disminución de existencias/valoración.
- Ejecutar actualización manual con fechas antiguas y recientes.
- Revisar próxima ejecución del cron en horario local.

### Inventario físico

- Escanear código válido, inexistente y duplicado.
- Contar productos con y sin lote.
- Consolidar múltiples lecturas/usuarios.
- Preparar quants y aplicar el ajuste desde Odoo.

### Interfaz

- Abrir productos y pickings en lectura.
- Editar, guardar, descartar y navegar con paginador.
- Revisar el chatter inferior del cierre en escritorio y móvil.
- Descargar y abrir el XLSX.

## Mantenimiento seguro

1. Añadir pruebas antes de cambiar fórmulas, estados o dominios.
2. No escribir directamente en capas de valoración o asientos.
3. Mantener la atomicidad; no introducir `commit()` manual.
4. Preservar `with_company()` y las reglas de compañía.
5. Evitar SQL salvo vistas de análisis o migraciones controladas.
6. Incrementar la versión del manifiesto en entregas desplegables.
7. Actualizar esta documentación cuando cambien modelos, campos, menús o procesos.

## Diagnóstico

Ante un error de actualización:

- revisar el traceback completo, no sólo el `RPC_ERROR` del navegador;
- validar dependencias y XML IDs;
- comprobar que la base seleccionada sea la correcta;
- revisar columnas/tablas antiguas antes de migrar;
- ejecutar la actualización con `--stop-after-init --workers=0`;
- verificar permisos y reglas con el mismo usuario que reproduce el problema.

Ante diferencias de costo o stock:

- conservar el batch y sus líneas como evidencia;
- revisar fecha de cierre, compañía, UoM, moneda y movimientos `done`;
- comparar `purchase_line_id`, recepciones y devoluciones;
- no corregir documentos históricos sin entender el impacto contable.

## Archivos que requieren revisión conjunta

| Cambio | Archivos relacionados |
|---|---|
| Nuevo modelo/campo | `models/`, `security/ir.model.access.csv`, reglas, vistas y pruebas |
| Nuevo menú/acción | vista correspondiente, `views/menus.xml` o menú temático, permisos |
| Nuevo activo web | `static/src/` y `__manifest__.py` |
| Dato de instalación | `data/` y orden del manifiesto |
| Reporte | `report/`, modelo abstracto y pruebas de PDF |
| Migración | método idempotente, función XML/hook, respaldo y prueba con datos reales |
