# Etiquetas personalizadas de productos

## Objetivo

Permitir que el usuario defina ancho y alto de etiquetas de producto y generar un PDF distribuido automáticamente sobre una hoja Carta.

## Extensión del asistente

`product.label.layout` añade el formato `custom` y los campos:

- `custom_label_width`, valor inicial 50 mm;
- `custom_label_height`, valor inicial 30 mm.

El área útil está definida por:

```text
Ancho útil:  190 mm
Alto útil:   250 mm
Separación:    5 mm
```

`_compute_dimensions()` calcula columnas y filas enteras que caben en esa superficie. Las dimensiones deben ser positivas y no pueden superar el área útil.

## Reporte

Cuando el formato es personalizado, `_prepare_report_data()` selecciona `action_report_product_label_custom` y transmite dimensiones, filas y columnas.

El reporte usa:

- formato de papel Carta sin márgenes adicionales;
- plantillas QWeb para `product.template` y `product.product`;
- cuadrícula y tamaños CSS calculados en `ReportProductTemplateLabelCustom`;
- ajuste dinámico de código de barras, textos y espacios según la altura.

## Control de páginas

`IrActionsReport._render_qweb_pdf()` interviene sólo cuando el reporte es `indoor_inventario.report_producttemplatelabel_custom`.

Calcula las páginas esperadas a partir del número de etiquetas y la capacidad por página. Si el motor QWeb genera páginas vacías adicionales, conserva únicamente las páginas esperadas mediante `PdfFileReader` y `PdfFileWriter`.

## Archivos

- `models/product_label_layout.py`: formato, dimensiones y validaciones.
- `models/product_label_report.py`: valores QWeb y recorte de páginas.
- `views/product_label_layout_views.xml`: campos del asistente.
- `report/product_label_reports.xml`: formato y acción.
- `report/product_label_templates.xml`: estructura visual.

## Consideraciones

- Las constantes representan el área útil de la hoja, no el tamaño físico completo.
- Cambiar márgenes o tamaño de papel requiere recalibrar las constantes y probar impresión a escala 100 %.
- El cálculo presupone una separación uniforme de 5 mm entre etiquetas.
