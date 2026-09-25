# Documentación técnica de Indoor Inventario

Esta carpeta describe la implementación vigente del addon `indoor_inventario` para Odoo 18. La documentación se basa en el código fuente del módulo, versión `18.0.6.0.0`.

## Alcance del módulo

El addon reúne las siguientes capacidades:

- cierre mensual y aplicación de costos estándar;
- productos provisionales para cotización, venta y compra;
- entregas de materiales a producción y detección de productos inmovilizados;
- sesiones de toma de inventario mediante lectura de códigos de barras;
- información de compra y factura por línea en recepciones;
- apertura en modo lectura de productos y operaciones de inventario;
- etiquetas de producto con dimensiones configurables;
- reportes, exportación XLSX, permisos y auditoría asociados.

## Índice temático

1. [Arquitectura y estructura del addon](01-arquitectura.md)
2. [Actualización mensual de costos estándar](02-costos-estandar.md)
3. [Productos provisionales](03-productos-provisionales.md)
4. [Entrega a producción y productos inmovilizados](04-produccion-e-inmovilizados.md)
5. [Toma de inventario](05-toma-de-inventario.md)
6. [Extensiones de recepciones](06-recepciones.md)
7. [Protección de formularios](07-proteccion-formularios.md)
8. [Etiquetas personalizadas](08-etiquetas.md)
9. [Seguridad, multicompañía y auditoría](09-seguridad-y-auditoria.md)
10. [Configuración, instalación y actualización](10-configuracion-y-despliegue.md)
11. [Pruebas y mantenimiento](11-pruebas-y-mantenimiento.md)

## Dependencias

El manifiesto declara las dependencias `stock_account`, `purchase_stock`, `sale_management` y `mail`. Estas incorporan, entre otros, los modelos de inventario, valoración, compras, ventas, productos y mensajería utilizados por el addon.

## Convenciones

- **Modelo nuevo**: tabla y lógica pertenecientes completamente a `indoor_inventario`.
- **Modelo heredado**: extensión de un modelo estándar de Odoo mediante `_inherit`.
- **Dato de instalación**: registro XML creado o ajustado al instalar o actualizar el addon.
- **SVL**: `stock.valuation.layer`, capa de valoración de inventario.
- **PPM**: precio promedio usado como propuesta de costo estándar mensual.

## Fuente de verdad

Si esta documentación difiere del comportamiento observado, prevalecen el código cargado en la base de datos, la configuración de la compañía y la versión exacta de Odoo 18 instalada. Después de modificar Python, XML, JavaScript, SCSS o datos del módulo se debe actualizar el addon y reiniciar los servicios cuando corresponda.
