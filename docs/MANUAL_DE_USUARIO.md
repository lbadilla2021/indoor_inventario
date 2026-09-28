# Manual de usuario — Indoor Inventario

## 1. Introducción

**Indoor Inventario** amplía las funciones de Inventario, Compras, Ventas y Productos de Odoo 18. Su objetivo es facilitar las siguientes tareas:

- revisar y actualizar mensualmente los costos estándar;
- cotizar artículos nuevos sin incorporarlos inmediatamente al maestro de productos;
- registrar entregas de materiales a producción;
- identificar productos que llevan mucho tiempo sin consumo;
- realizar tomas de inventario con códigos de barras;
- consultar precios y facturas por línea en las recepciones;
- proteger fichas y operaciones contra modificaciones accidentales;
- imprimir etiquetas con dimensiones personalizadas.

Este manual está dirigido a usuarios de inventario, compras, ventas, costos y responsables de bodega.

> **Importante:** los menús y botones disponibles dependen de los permisos asignados al usuario y de las aplicaciones instaladas en la base de datos.

---

## 2. Perfiles y responsabilidades

### 2.1 Usuario de inventario

Puede trabajar con productos, recepciones, entregas, transferencias, conteos y sesiones de inventario, según sus permisos estándar de Odoo.

### 2.2 Administrador de inventario

Además de las funciones normales, puede:

- preparar ajustes de inventario físico desde una sesión;
- eliminar sesiones o lecturas cuando corresponda;
- consultar el consolidado de sesiones de inventario;
- mantener la configuración general de Inventario.

### 2.3 Analista de costos

Puede:

- crear cierres mensuales de costo estándar;
- incluir productos en la política de costo mensual;
- calcular y recalcular costos;
- revisar compras, diferencias y alertas;
- consultar el historial de costos.

### 2.4 Aprobador de costos

Incluye las funciones del analista y además puede:

- aprobar el costo propuesto;
- modificar el PPM aprobado antes de aprobar;
- aplicar el nuevo costo a los productos.

### 2.5 Usuarios de ventas y compras

Pueden crear y utilizar productos provisionales desde cotizaciones, pedidos de venta y solicitudes u órdenes de compra.

---

## 3. Mapa de navegación

Las principales opciones se encuentran en la aplicación **Inventario**.

| Función | Ubicación habitual |
|---|---|
| Inventariar | Inventario > Inventariar |
| Sesiones de inventario | Inventario > Operaciones > Sesiones Inventario |
| Entrega a Producción | Inventario > Información general o tipo de operación correspondiente |
| Actualización de costos | Inventario > Operaciones > Actualización de Costos Estándar |
| Productos provisionales | Inventario > Productos > Productos provisionales |
| Historial de costos | Inventario > Reportes > Historial de costos estándar |
| Diagnóstico de costo | Inventario > Reportes > Diagnóstico de método de costo |
| Consolidado de conteos | Inventario > Reportes > Sesiones Inventario |
| Parámetros | Inventario > Configuración > Ajustes |

Si una opción no aparece, solicite al administrador que revise sus grupos y compañías habilitadas.

---

## 4. Preparación inicial

Antes de comenzar a operar, un administrador debe revisar la configuración.

### 4.1 Parámetros de costos estándar

Ingrese a **Inventario > Configuración > Ajustes** y busque **Costos estándar mensuales**.

Configure:

1. **Compras consideradas:** número de compras que formarán el promedio. Se admiten entre 1 y 3.
2. **Antigüedad de compra:** días después de los cuales una compra se considera antigua.
3. **Umbral de advertencia:** porcentaje de variación que mostrará una advertencia.
4. **Umbral crítico:** porcentaje de variación que mostrará una alerta crítica.

Valores iniciales recomendados:

- 3 compras;
- 180 días;
- advertencia sobre 10 %;
- crítico sobre 20 %.

Pulse **Guardar** después de modificar los valores.

### 4.2 Parámetro de inmovilización

En la misma pantalla busque **Control de productos inmovilizados**.

1. Indique los **meses sin consumo** que deben transcurrir para considerar un producto inmovilizado.
2. El valor mínimo es un mes.
3. Pulse **Actualizar ahora** para ejecutar inmediatamente la revisión.

El sistema también realiza esta actualización automáticamente cada noche a las 03:00, considerando la zona horaria configurada para la compañía.

### 4.3 Estructura de producción

La instalación prepara por almacén:

- la ubicación **Producción/Consumo materiales**;
- el tipo de operación **Entrega a Producción**;
- origen por defecto en la ubicación principal de stock;
- destino por defecto en Consumo materiales.

Antes de usarla, revise que las ubicaciones correspondan al almacén correcto.

---

## 5. Consulta y edición segura de productos y operaciones

Las fichas de productos y los formularios de operaciones de inventario se abren en modo de sólo lectura.

### Para consultar

1. Abra el producto, recepción, entrega o transferencia.
2. Navegue por sus pestañas y campos normalmente.
3. Mientras no pulse **Editar**, no podrá cambiar valores accidentalmente.

### Para modificar

1. Pulse **Editar** en la parte superior.
2. Realice los cambios autorizados.
3. Pulse **Guardar**.
4. El formulario volverá automáticamente al modo de consulta.

Si pulsa **Descartar** o cambia al registro siguiente, el sistema también vuelve al modo de lectura.

> Esta protección evita errores de interfaz, pero no reemplaza los permisos del usuario ni las reglas de aprobación internas.

---

## 6. Actualización mensual de costos estándar

### 6.1 Objetivo del proceso

El cierre mensual calcula un costo sugerido utilizando las últimas compras efectivamente recibidas. El proceso separa cuatro actividades:

1. calcular;
2. revisar;
3. aprobar;
4. aplicar.

El sistema no cambia automáticamente el costo al recibir una compra. El nuevo costo entra en vigencia únicamente cuando un aprobador aplica el cierre.

### 6.2 Preparación de los productos

Cada producto que participará debe cumplir lo siguiente:

- ser un producto almacenable;
- tener activada la opción **Usar costo estándar mensual**;
- pertenecer a una categoría con método de costo **Precio estándar**.

Para revisar incompatibilidades ingrese a:

**Inventario > Reportes > Diagnóstico de método de costo**.

Este reporte muestra productos marcados para el proceso mensual cuya categoría todavía utiliza AVCO o FIFO. El sistema no cambia el método automáticamente.

#### Incorporación masiva

En un cierre nuevo puede pulsar **Incluir productos elegibles**. El sistema marcará los productos almacenables que ya usan costo estándar.

Use esta acción con cuidado, porque incorpora varios productos a la política mensual.

### 6.3 Crear el cierre

1. Ingrese a **Inventario > Operaciones > Actualización de Costos Estándar**.
2. Pulse **Nuevo**.
3. Seleccione la compañía, si trabaja con varias.
4. Indique la **Fecha de cierre**.
5. Agregue notas si necesita documentar el período o alguna consideración.
6. Pulse **Calcular**.

La fecha no puede estar en el futuro.

### 6.4 Cómo selecciona las compras

Para cada producto, el sistema considera las compras más recientes que tengan recepciones terminadas hasta el final de la fecha de cierre.

- Una recepción parcial aporta sólo la cantidad realmente recibida.
- Varias recepciones de una misma línea de compra se consolidan.
- Una devolución válida a proveedor reduce la cantidad recibida.
- Compras canceladas o recepciones futuras no participan.
- Cantidades y precios se convierten a la unidad del producto.
- Monedas extranjeras se convierten a la moneda de la compañía usando la fecha de recepción.

El cálculo es:

```text
PPM = suma de (cantidad recibida × precio convertido)
      ------------------------------------------------
                 suma de cantidades recibidas
```

Con dos o una compra se usan sólo las disponibles. Sin compras, el producto conserva su costo anterior y muestra una alerta.

### 6.5 Revisar la planilla

Después de calcular, la pestaña **Revisión** muestra una línea por producto.

| Columna | Significado |
|---|---|
| Producto | Producto evaluado |
| Categoría | Categoría del producto |
| Cantidad stock | Existencia a la fecha de cierre |
| PPM anterior | Costo estándar vigente antes del cierre |
| Cant 1, 2 y 3 | Cantidad recibida en cada compra |
| Precio 1, 2 y 3 | Precio convertido de cada compra |
| PPM | Costo calculado por el sistema |
| PPM Aprobado | Costo que se aplicará después de aprobar |
| Diferencia $ | Diferencia entre costo aprobado y costo anterior |
| Diferencia % | Variación porcentual |
| Nuevo Inventario | Stock de cierre valorizado al costo aprobado |
| Diferencia Inventario | Cambio estimado de valorización |
| Estado | Resultado de las validaciones |
| Alerta | Explicación de la excepción |

El resumen superior muestra:

- cantidad de productos;
- inventario anterior;
- nuevo inventario;
- diferencia total de inventario.

#### Consultar compras de una línea

Abra la línea del producto para ver el detalle de cada compra:

- orden de compra;
- línea de orden;
- proveedor;
- fecha de recepción;
- cantidad y precio;
- recepciones asociadas.

Los enlaces permiten navegar a los documentos originales.

### 6.6 Estados y alertas

| Estado | Qué significa | Acción recomendada |
|---|---|---|
| Listo | Puede aplicarse | Revisar diferencias |
| Sin compras | No existen compras utilizables | Confirmar si debe conservarse el costo anterior |
| Compra obsoleta | La compra supera la antigüedad permitida | Revisar vigencia del precio |
| Método inválido | El producto no usa precio estándar | Corregir categoría o excluirlo |
| Stock negativo | Existencia negativa al cierre | Corregir stock y recalcular |

El stock negativo bloquea la aplicación completa. Una línea con método inválido no recibe el nuevo costo.

### 6.7 Ajustar el costo aprobado

Mientras el cierre está **Calculado**, el aprobador puede modificar **PPM Aprobado**.

1. Edite sólo el valor aprobado.
2. No ingrese costos negativos.
3. Documente en las notas la razón del ajuste.
4. Revise nuevamente las diferencias y el valor de inventario.

El PPM calculado no se pierde; queda disponible para comparar con el valor aprobado.

### 6.8 Recalcular

Pulse **Recalcular** si se corrigieron recepciones, stock, compras o parámetros antes de aprobar.

> El recálculo reconstruye las líneas. Cualquier ajuste manual en PPM Aprobado debe revisarse nuevamente.

### 6.9 Aprobar y aplicar

#### Aprobar

1. Confirme que no existan errores críticos.
2. Verifique el PPM aprobado y las notas.
3. Pulse **Aprobar**.

Después de aprobar las líneas dejan de ser editables.

#### Aplicar costos

1. Pulse **Aplicar costos**.
2. Lea el mensaje de confirmación.
3. Confirme la operación.

Odoo actualiza el costo estándar vigente. Cuando la categoría usa valoración automática y tiene sus cuentas y diario correctamente configurados, Odoo genera la revalorización y el asiento correspondientes.

Un cierre aplicado:

- no puede cancelarse;
- no puede modificarse;
- no puede eliminarse;
- no puede repetirse para la misma compañía y fecha.

### 6.10 Exportar a Excel

1. Abra un cierre con líneas calculadas.
2. Pulse **Exportar Excel**.
3. Guarde el archivo descargado.

El archivo contiene las mismas columnas principales de la tabla, filtros y encabezados. Puede utilizarse para revisión, respaldo o análisis externo.

### 6.11 Consultar historial

Ingrese a **Inventario > Reportes > Historial de costos estándar**.

Puede:

- consultar por producto, categoría, compañía o período;
- agrupar por mes;
- usar lista o tabla dinámica;
- acceder desde el botón de historial de la ficha del producto.

---

## 7. Productos provisionales

### 7.1 Cuándo utilizarlos

Use un producto provisional cuando necesita cotizar o comprar un artículo que todavía no debe incorporarse al maestro definitivo.

Ejemplos:

- solicitud especial de un cliente;
- producto nuevo sujeto a aprobación;
- material del que aún no se conocen todos los datos;
- cotización que podría no concretarse.

### 7.2 Crear un provisional

1. Ingrese a **Inventario > Productos > Productos provisionales**.
2. Pulse **Nuevo**.
3. Complete el nombre y, si corresponde, la descripción.
4. Seleccione la compañía.
5. Defina obligatoriamente:
   - categoría;
   - tipo de producto;
   - unidad de medida;
   - unidad de compra;
   - ruta de compra.
6. Revise las casillas **Ventas** y **Compras**, marcadas inicialmente.
7. Guarde.

Para bienes, el tipo inicial es **Bien**. El costo no es obligatorio en esta etapa.

### 7.3 Estados del provisional

| Estado | Significado |
|---|---|
| Borrador | Registro en preparación |
| Cotizado | Ya fue utilizado en una línea de venta o compra |
| Aprobado | Fue revisado internamente |
| Convertido | Ya existe un producto definitivo asociado |
| Descartado | No continuará el proceso |

Un provisional descartado puede volver a borrador. Uno convertido no puede descartarse.

### 7.4 Usarlo en una cotización de venta

1. Cree la cotización.
2. En una línea, seleccione **Producto Provisional** en la columna Producto.
3. Aparecerá el campo **Producto provisional**.
4. Seleccione un provisional existente o cree uno desde el desplegable.
5. Complete cantidad y precio de venta.
6. Guarde o envíe la cotización.

Al confirmar la venta, el provisional se convierte automáticamente en producto definitivo si todavía no existe, y la línea reemplaza el marcador por ese producto.

### 7.5 Usarlo en una solicitud u orden de compra

1. Cree la solicitud de cotización.
2. En **Producto**, seleccione **Producto Provisional**.
3. Seleccione el registro en **Producto provisional**.
4. Complete cantidad, unidad y precio.
5. Confirme la orden.

Al confirmar:

- se crea o vincula el producto definitivo;
- la línea se actualiza con el producto real;
- el costo se obtiene del precio de compra;
- la moneda y la unidad se convierten cuando sea necesario;
- si hay varias líneas del mismo provisional, el costo se pondera por cantidad.

### 7.6 Conversión manual

Desde el formulario provisional puede pulsar **Convertir**. Si seleccionó un producto definitivo existente, se vinculará. En caso contrario se creará uno nuevo con la categoría, tipo, unidades, ruta e indicadores definidos.

La conversión manual sin una compra confirmada puede dejar el costo inicial sin valor. Posteriormente podrá definirse mediante el proceso correspondiente.

---

## 8. Recepciones de compras

### 8.1 Consultar la orden de compra

En una recepción proveniente de compras, junto al **Documento origen** aparece un botón con flecha/enlace.

1. Pulse el botón.
2. La orden de compra se abrirá en una ventana modal.
3. Consulte productos, precios, condiciones y proveedor.
4. Cierre la ventana para regresar a la recepción.

La orden se muestra en modo de consulta.

### 8.2 Precio de compra por línea

En el detalle de la recepción, la columna **Precio compra** muestra el precio unitario registrado en la línea de la orden y su moneda.

Este valor es informativo. Modificar la cantidad recibida no cambia el precio de la orden.

### 8.3 Factura del proveedor por línea

La columna **Factura** permite registrar el número de factura correspondiente a cada movimiento.

Esto permite que una misma recepción contenga productos respaldados por facturas diferentes.

1. Antes de validar la recepción, escriba el número de factura en cada línea.
2. Repita el mismo número cuando varias líneas pertenezcan a la misma factura.
3. Valide la recepción.

Después de terminar o cancelar el movimiento, el dato queda de sólo lectura.

> Este campo es una referencia logística. No crea una factura contable ni reemplaza el proceso de Facturación/Contabilidad.

---

## 9. Entrega de materiales a producción

### 9.1 Cuándo usarla

Use **Entrega a Producción** para retirar de bodega materiales entregados al área productiva mientras todavía no se utilizan órdenes de fabricación.

### 9.2 Registrar una entrega

1. Abra el tipo de operación **Entrega a Producción** desde Inventario.
2. Pulse **Nuevo**.
3. Confirme el origen, normalmente el stock principal del almacén.
4. Confirme el destino **Producción/Consumo materiales**.
5. Agregue los productos y cantidades entregadas.
6. Guarde y valide la operación.

Al validar, los materiales dejan la ubicación interna de bodega. Esto reduce las existencias disponibles y produce el efecto de valoración estándar correspondiente a una salida hacia producción.

### 9.3 Buenas prácticas

- No utilice una sububicación interna de `WH/Stock` como destino si necesita que el material salga de la valorización de bodega.
- No cambie el destino de Consumo materiales sin autorización.
- Registre la fecha y las cantidades reales de entrega.
- Corrija devoluciones desde producción mediante movimientos trazables, no modificando transferencias terminadas.

---

## 10. Productos inmovilizados

### 10.1 Qué significa la marca

Un producto queda **Inmovilizado** cuando su último movimiento terminado desde una bodega hacia **Producción/Consumo materiales** es anterior al límite de meses configurado.

La marca mide falta de consumo productivo. No considera como consumo:

- transferencias entre ubicaciones internas;
- recepciones de compras;
- ajustes que no terminan en Consumo materiales;
- movimientos todavía no validados.

Un producto sin ningún consumo registrado no se marca automáticamente.

### 10.2 Actualización automática

Cada noche a las 03:00 el sistema:

1. revisa los productos almacenables;
2. identifica la fecha de su último consumo;
3. marca los que superan el límite;
4. libera los que volvieron a tener consumo reciente.

### 10.3 Actualización manual

1. Ingrese a **Inventario > Configuración > Ajustes**.
2. Busque **Control de productos inmovilizados**.
3. Pulse **Actualizar ahora**.
4. Revise la notificación con productos evaluados, inmovilizados, marcados y liberados.

### 10.4 Consultar productos inmovilizados

En el maestro de productos utilice el filtro **Inmovilizados**. La ficha muestra también la fecha del último consumo detectado.

---

## 11. Toma de inventario

### 11.1 Conceptos

- **Sesión:** agrupa una toma de inventario para una ubicación.
- **Lectura:** registro individual de producto, cantidad, usuario, fecha y lote.
- **Consolidado:** suma lecturas y las compara con la existencia actual.
- **Preparar inventario físico:** transfiere las cantidades contadas al ajuste estándar de Odoo para revisión.
- **Aplicar ajuste:** operación final realizada desde Inventario físico de Odoo.

### 11.2 Crear una sesión

1. Ingrese a **Inventario > Operaciones > Sesiones Inventario**.
2. Pulse **Nuevo**.
3. Revise la referencia automática.
4. Seleccione la ubicación a contar.
5. Asigne el responsable.
6. Agregue una nota si necesita indicar sector, turno o alcance.
7. Pulse **Iniciar** o comience a registrar lecturas.

Estados disponibles:

```text
Borrador -> En proceso -> En revisión -> Cerrado
```

Una sesión puede cancelarse mientras el proceso lo permita.

### 11.3 Registrar lecturas

1. Ingrese a **Inventario > Inventariar**.
2. Seleccione o confirme la sesión.
3. Escanee el código de barras.
4. El sistema buscará el producto y moverá el foco a la cantidad.
5. Indique la cantidad contada.
6. Si el producto usa lote o serie, seleccione el dato correspondiente.
7. Confirme/guarde la lectura.
8. Repita para los demás productos.

La cantidad debe ser mayor que cero.

#### Mensajes habituales

- **Producto no encontrado:** el código no existe en el maestro.
- **Código duplicado:** más de un producto tiene el mismo código.
- **Debe indicar lote o serie:** el producto tiene seguimiento obligatorio.
- **Sesión cerrada o en revisión:** no admite nuevas lecturas.

Una misma combinación de producto y lote puede registrarse varias veces. El consolidado sumará las lecturas.

### 11.4 Enviar a revisión

Cuando termine el conteo:

1. Abra la sesión.
2. Revise número de lecturas, productos, último usuario y última fecha.
3. Pulse **Enviar a revisión**.

Desde ese momento no deben agregarse ni modificarse lecturas.

### 11.5 Revisar el consolidado

Ingrese a **Inventario > Reportes > Sesiones Inventario** y seleccione o agrupe por sesión.

Revise:

- cantidad contada;
- cantidad actual en Odoo;
- diferencia;
- número de lecturas;
- usuarios participantes;
- fecha de última lectura.

Investigue diferencias inusuales antes de preparar el ajuste.

### 11.6 Preparar el inventario físico

Esta acción requiere permisos de administrador de inventario.

1. Abra una sesión en estado **En revisión**.
2. Pulse **Preparar inventario físico**.
3. El sistema abrirá los quants preparados en la vista estándar.
4. Revise producto, ubicación, lote, cantidad actual y cantidad inventariada.
5. Corrija datos si corresponde.
6. Aplique el ajuste desde la función estándar de Inventario.

> Preparar no significa aplicar. El stock sólo cambia cuando el ajuste se aplica en Odoo.

### 11.7 Cerrar la sesión

Después de preparar y revisar el inventario:

1. Regrese a la sesión.
2. Confirme quién preparó y la cantidad de líneas.
3. Verifique que el ajuste se haya tratado según el procedimiento interno.
4. Pulse **Cerrar**.

No se puede cerrar una sesión que no haya preparado previamente el inventario físico.

---

## 12. Etiquetas personalizadas

### 12.1 Crear etiquetas

1. Seleccione uno o varios productos.
2. Ejecute la acción estándar **Imprimir etiquetas**.
3. En formato seleccione **Personalizado**.
4. Indique:
   - ancho en milímetros;
   - alto en milímetros.
5. Revise las filas y columnas calculadas.
6. Indique la cantidad de etiquetas.
7. Genere el PDF.

### 12.2 Límites

- ancho máximo del área útil: 190 mm;
- alto máximo del área útil: 250 mm;
- ambas dimensiones deben ser mayores que cero;
- separación prevista entre etiquetas: 5 mm.

Imprima a escala 100 % y realice una prueba antes de utilizar una gran cantidad de hojas.

---

## 13. Reportes y consultas

### 13.1 Historial de costos estándar

Úselo para analizar costos, diferencias y valorización por mes, producto o categoría. La tabla dinámica permite cambiar filas, columnas y medidas.

### 13.2 Diagnóstico de método de costo

Úselo antes del cierre para encontrar productos bajo política mensual que todavía no usan precio estándar.

### 13.3 Sesiones Inventario

Muestra el consolidado de conteos. Es útil para comparar sesiones, diferencias y participación de usuarios.

### 13.4 Ficha del producto

La ficha incluye:

- política de costo mensual;
- último cálculo y última aplicación;
- último costo calculado y aprobado;
- acceso al historial;
- marca de inmovilizado;
- fecha del último consumo en producción.

---

## 14. Recomendaciones de operación

### Antes del cierre mensual

1. Termine recepciones, devoluciones y entregas pendientes.
2. Corrija existencias negativas.
3. Complete el inventario físico del período.
4. Revise productos con método de costo incompatible.
5. Confirme tasas de cambio y configuración contable.
6. Calcule el cierre y revise excepciones antes de aprobar.

### Para productos provisionales

- Use nombres descriptivos que permitan identificarlos.
- Defina la categoría correcta antes de convertir.
- No reutilice un provisional para productos distintos.
- Descarte los registros que no continuarán.

### Para conteos

- Cree una sesión por ubicación y período de conteo.
- Evite movimientos simultáneos durante el conteo cuando sea posible.
- Identifique correctamente lotes y series.
- No aplique diferencias sin revisar el consolidado.

### Para entrega a producción

- Use siempre el tipo de operación preparado para este fin.
- Valide movimientos sólo cuando la entrega haya ocurrido.
- Evite destinos internos que mantengan el material dentro de bodega.

---

## 15. Solución de problemas

### No aparece un producto en el cierre

Revise que:

- sea almacenable;
- tenga **Usar costo estándar mensual** activado;
- pertenezca a la compañía correcta;
- esté activo.

### El producto aparece con Método inválido

La categoría usa AVCO o FIFO. Solicite una revisión contable antes de cambiar el método. El módulo no lo cambia automáticamente.

### El cierre no permite aplicar

Compruebe:

- que esté aprobado;
- que no existan productos con stock negativo;
- que el usuario sea aprobador;
- que no exista otro cierre aplicado para la misma fecha y compañía.

### No se generó un asiento de revalorización

Revise:

- si la categoría usa valoración automática;
- cuentas y diario de inventario;
- existencia positiva valorizada;
- permisos contables;
- que realmente haya cambiado el costo.

Con valoración manual, el costo puede cambiar sin asiento automático.

### No aparece Producto provisional

Primero seleccione **Producto Provisional** en la columna Producto. El campo adicional sólo se activa para esas líneas.

### No puedo confirmar una orden con Producto Provisional

Existe una línea con el marcador, pero sin un registro provisional seleccionado. Complete el campo **Producto provisional** en todas las líneas marcadas.

### No aparece la flecha del documento origen

El botón sólo aparece en recepciones vinculadas a una orden de compra. Revise que la recepción conserve `purchase_id` y el documento de origen correcto.

### Un producto no aparece como inmovilizado

Revise:

- meses configurados;
- fecha del último consumo;
- que el movimiento esté terminado;
- que el destino sea Consumo materiales;
- que exista al menos un consumo histórico.

Después pulse **Actualizar ahora**.

### No puedo preparar el inventario físico

Compruebe que:

- sea administrador de inventario;
- la sesión esté En revisión;
- existan lecturas;
- el consolidado tenga registros.

### El lector no encuentra el producto

Verifique el código de barras en la ficha del producto. No debe estar vacío ni duplicado.

### No puedo editar un producto o una recepción

Los registros existentes abren en consulta. Pulse **Editar**. Si el botón no aparece o la escritura es rechazada, solicite revisión de permisos.

---

## 16. Glosario

| Término | Definición |
|---|---|
| Cierre de costos | Documento mensual que calcula, aprueba y aplica costos estándar |
| PPM | Costo promedio ponderado calculado con compras recibidas |
| PPM aprobado | Costo autorizado para aplicar al producto |
| Costo estándar | Costo vigente almacenado por Odoo para productos con método estándar |
| Revalorización | Cambio del valor de inventario originado por una variación de costo |
| SVL | Capa de valoración de inventario generada por Odoo |
| Producto provisional | Artículo temporal que todavía no forma parte del maestro definitivo |
| Producto marcador | Producto técnico “Producto Provisional” usado dentro de una línea estándar |
| Consumo materiales | Ubicación de producción que representa salida desde bodega |
| Inmovilizado | Producto cuyo último consumo productivo supera el límite configurado |
| Sesión de inventario | Agrupación de lecturas de una toma física |
| Consolidado | Comparación entre cantidades contadas y existencias actuales |
| Quant | Registro de existencia de un producto en una ubicación, lote, paquete y propietario |

---

## 17. Soporte

Al solicitar soporte entregue:

- compañía y usuario afectado;
- nombre o referencia del documento;
- fecha y hora aproximada;
- pasos realizados;
- mensaje completo del error;
- captura de pantalla;
- resultado esperado y resultado observado.

No modifique documentos históricos ni elimine cierres, sesiones o movimientos para ocultar un error. Conserve la información para facilitar el diagnóstico y la auditoría.
