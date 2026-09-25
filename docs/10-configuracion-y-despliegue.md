# Configuración, instalación y actualización

## Requisitos previos

- Odoo 18 con los addons `stock_account`, `purchase_stock`, `sale_management` y `mail` disponibles.
- Base de datos respaldada antes de instalar o actualizar en producción.
- Categorías, monedas, tasas, cuentas y diarios configurados según los procesos utilizados.
- Ruta del addon incluida en `addons_path`; en el entorno documentado se monta como `/mnt/extra-addons/indoor_inventario`.

## Instalación

Ejemplo para el entorno Docker actual:

```bash
docker exec odoo bash -lc 'odoo -d NOMBRE_BD -i indoor_inventario --stop-after-init --workers=0 --db_host="$HOST" --db_user="$USER" --db_password="$PASSWORD"'
docker compose -f C:/odoo/docker-compose.yml restart odoo
```

Reemplace `NOMBRE_BD` sólo después de verificar el destino. No ejecute una instalación en producción sin respaldo y ventana de mantenimiento.

## Actualización

```bash
docker exec odoo bash -lc 'odoo -d NOMBRE_BD -u indoor_inventario --stop-after-init --workers=0 --db_host="$HOST" --db_user="$USER" --db_password="$PASSWORD"'
docker compose -f C:/odoo/docker-compose.yml restart odoo
```

La actualización es necesaria después de cambios en modelos, campos, XML, ACL, datos, reportes o activos declarados en el manifiesto. Reinicie Odoo para descartar cachés Python; los bundles web pueden requerir recarga forzada del navegador.

## Efectos de instalación/actualización

Las funciones XML realizan operaciones idempotentes:

- sincronizan el nombre visible **Indoor Inventario** en los idiomas activos;
- crean o reutilizan Producción/Consumo materiales y Entrega a Producción;
- configuran el producto marcador **Producto Provisional**;
- programan el cron de inmovilizados a las 03:00 locales;
- migran sesiones desde `ziv_cod_barra` si sus tablas existen.

No se eliminan ubicaciones, tipos de operación ni documentos de negocio.

## Configuración funcional

### Costos estándar

En **Inventario > Configuración > Ajustes**:

- compras consideradas: 1 a 3;
- antigüedad de compra: 180 días inicialmente;
- advertencia: 10 % inicialmente;
- crítico: 20 % inicialmente.

En cada plantilla almacenable se activa **Usar costo estándar mensual**. El reporte de diagnóstico identifica productos seleccionados cuyo método todavía es AVCO/FIFO.

### Inmovilización

Configure `Meses sin consumo para inmovilizar`, mínimo 1. Verifique que cada almacén tenga:

- tipo de operación **Entrega a Producción**;
- origen en la ubicación principal de stock;
- destino **Producción/Consumo materiales**;
- marcas técnicas Indoor activas.

### Productos provisionales

Verifique que la ruta Comprar estándar exista y sea seleccionable. Los usuarios deben pertenecer al menos a ventas, compras o inventario para acceder al maestro provisional.

### Toma de inventario

Asigne permisos de inventario. Sólo administradores pueden preparar el ajuste físico. En productos con seguimiento, los lectores deben capturar lote o serie.

## Parámetros técnicos

| Clave | Descripción |
|---|---|
| `indoor_costos_estandar.purchase_count` | Cantidad de compras consideradas |
| `indoor_costos_estandar.stale_days` | Antigüedad de compra |
| `indoor_costos_estandar.warning_threshold` | Umbral de advertencia |
| `indoor_costos_estandar.critical_threshold` | Umbral crítico |
| `indoor_inventario.immobilization_months` | Meses sin consumo productivo |

Los nombres históricos `indoor_costos_estandar.*` se mantienen por compatibilidad de datos aunque el addon se llame `indoor_inventario`.

## Lista de verificación posterior

1. Confirmar que la aplicación aparece como **Indoor Inventario**.
2. Revisar menús y grupos con un usuario no administrador.
3. Confirmar ubicación y tipo de operación de producción por almacén.
4. Revisar la próxima ejecución del cron y la zona horaria de la compañía.
5. Crear un provisional de prueba y convertirlo desde una compra.
6. Crear una sesión de inventario y preparar un quant sin aplicar diferencias ficticias en producción.
7. Calcular un cierre de prueba y revisar compras, moneda, UoM y stock histórico.
8. Verificar descarga XLSX y reportes.

## Desinstalación y datos

La desinstalación de un módulo Odoo puede eliminar tablas y registros propios. Antes de desinstalar:

- exporte cierres, líneas, provisionales y sesiones necesarios;
- respalde la base;
- compruebe dependencias personalizadas;
- no elimine `ziv_cod_barra` hasta validar la migración completa si todavía está presente.
