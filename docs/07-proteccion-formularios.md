# Protección de formularios

## Objetivo

Abrir registros existentes en modo lectura para reducir cambios accidentales. El usuario debe pulsar **Editar** antes de modificar.

## Alcance

La constante `PROTECTED_MODELS` contiene:

- `product.template`;
- `product.product`;
- `stock.picking`.

Por lo tanto cubre fichas de productos y formularios de operaciones de inventario como recepciones, entregas y transferencias internas. No afecta formularios de otros modelos.

## Implementación

`static/src/js/protected_form_mode.js` aplica un patch acotado a `FormController`:

- fuerza `mode = readonly` al abrir un registro existente protegido;
- expone el estado usado por la plantilla OWL;
- implementa `enterIndoorEditMode()`;
- vuelve a lectura después de guardar o descartar;
- mantiene edición en registros nuevos;
- vuelve a lectura al cambiar de registro mediante el paginador.

`static/src/xml/protected_form_mode.xml` hereda `web.FormView` y `web.FormView.Buttons` para insertar el botón **Editar** tanto en formularios normales como en diálogos.

## Comportamiento esperado

| Situación | Resultado |
|---|---|
| Abrir registro existente protegido | Sólo lectura |
| Pulsar Editar | Entra explícitamente a edición |
| Guardar | Regresa a sólo lectura |
| Descartar | Regresa a sólo lectura |
| Crear registro nuevo | Permanece editable |
| Navegar al registro siguiente/anterior | El nuevo registro abre en lectura |

## Alcance de seguridad

Esta función es una protección de interfaz, no una regla de acceso. No bloquea escrituras por RPC, importaciones, procesos automáticos o código servidor. Los permisos reales siguen dependiendo de ACL, reglas de registro y validaciones del modelo.

Para añadir otro formulario se debe incorporar su `resModel` a `PROTECTED_MODELS` y probar creación, guardado, descarte, navegación y uso en diálogos.
