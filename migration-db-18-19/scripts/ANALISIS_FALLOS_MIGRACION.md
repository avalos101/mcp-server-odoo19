# Análisis Profundo de Fallos en la Migración

## Problemas Identificados

### 1. **Problema: Campos Many2many y One2many no se migran correctamente**

**Síntoma:**
- Las cotizaciones migran sin líneas de productos (`order_line`)
- Los productos no tienen variantes migradas
- Las relaciones many2many no se preservan

**Causa Raíz:**
- El script actual intenta migrar `order_line` como campo directo, pero en Odoo esto es un campo one2many que requiere un formato especial
- Los campos one2many/many2many requieren usar comandos Odoo: `[(0, 0, {...})]` para crear, `[(6, 0, [ids])]` para reemplazar

**Impacto:**
- **Crítico**: Sin líneas de productos, las cotizaciones no tienen información de productos, cantidades, precios
- Las cotizaciones quedan inutilizables para procesos de negocio

### 2. **Problema: Mapeo de IDs incompleto o incorrecto**

**Síntoma:**
- Facturas no se migran porque partners no están en el mapeo
- Tareas no se migran porque proyectos no están en el mapeo
- Relaciones many2one fallan porque los IDs referenciados no existen

**Causa Raíz:**
- El mapeo de IDs se guarda solo cuando un registro se crea exitosamente
- Si un registro falla en la creación, su ID no se guarda en el mapeo
- Los registros dependientes no pueden encontrar sus relaciones

**Impacto:**
- **Alto**: Datos relacionados se pierden
- Integridad referencial rota

### 3. **Problema: Campos de metadatos (create_date, write_date) no se preservan**

**Síntoma:**
- Fechas de creación incorrectas
- Historial de modificaciones perdido

**Causa Raíz:**
- Odoo no permite actualizar `create_date` y `write_date` directamente vía XML-RPC
- Estos campos son automáticos y solo se pueden establecer durante la creación inicial
- El script actual no maneja esto correctamente

**Impacto:**
- **Medio**: Pérdida de trazabilidad histórica
- Fechas incorrectas pueden afectar reportes y análisis

### 4. **Problema: Validaciones de Odoo 19 más estrictas**

**Síntoma:**
- Errores de validación al crear registros
- Campos requeridos que no se detectan correctamente
- Valores que funcionaban en Odoo 18 pero fallan en Odoo 19

**Causa Raíz:**
- Odoo 19 tiene validaciones más estrictas
- Algunos campos cambiaron de tipo o validación
- Campos computados o relacionados requieren dependencias instaladas

**Impacto:**
- **Alto**: Muchos registros fallan en la creación
- Datos incompletos en destino

### 5. **Problema: Usuarios no migrados correctamente**

**Síntoma:**
- Comerciales (user_id) no se asignan correctamente
- `create_uid` y `write_uid` apuntan a admin en lugar de usuarios reales

**Causa Raíz:**
- El script intenta migrar usuarios pero falla en muchos casos (844 errores de 844 usuarios)
- El mapeo de usuarios no se completa
- Los registros se crean con usuario admin por defecto

**Impacto:**
- **Crítico**: Sin comercial asignado, las cotizaciones no tienen responsable
- Pérdida de información de quién creó/modificó cada registro

### 6. **Problema: Campos calculados y dependencias**

**Síntoma:**
- Campos que dependen de otros módulos no se migran
- Campos computados fallan porque sus dependencias no están disponibles

**Causa Raíz:**
- El script intenta migrar todos los campos sin verificar si son computados
- Algunos campos requieren que otros módulos estén instalados
- Campos que dependen de configuraciones del sistema

**Impacto:**
- **Medio**: Algunos datos no se migran pero no son críticos

### 7. **Problema: Manejo de errores silencioso**

**Síntoma:**
- El script continúa aunque haya errores
- Los errores se registran pero no se corrigen
- No hay reintentos ni estrategias de recuperación

**Causa Raíz:**
- El script está diseñado para continuar aunque falle
- No hay lógica de reintento
- No hay validación previa de datos

**Impacto:**
- **Alto**: Muchos datos se pierden sin que se sepa por qué
- Difícil diagnosticar problemas

## Estadísticas de Fallos

### Por Modelo:

1. **res.users**: 0/844 migrados (0%) - **CRÍTICO**
   - Todos los usuarios fallan
   - Sin usuarios, no se pueden mapear create_uid/write_uid

2. **product.product**: 3/789 migrados (0.4%) - **CRÍTICO**
   - Solo 3 variantes de productos migradas
   - Sin variantes, los productos no son funcionales

3. **crm.lead**: 3,023/3,181 migrados (95.1%) - **BUENO**
   - Relativamente exitoso
   - 158 errores menores

4. **sale.order**: 1,984/1,986 migrados (99.9%) - **BUENO**
   - Casi todas migradas
   - PERO: Sin líneas, sin comercial, sin fechas correctas

5. **account.move**: 0/36 migrados (0%) - **CRÍTICO**
   - Ninguna factura migrada
   - Partners no están en mapeo

6. **project.task**: 0/317 migrados inicialmente, luego 60/317 (18.9%) - **MALO**
   - Campo user_id incorrecto (corregido)
   - Proyectos no mapeados

## Causas Fundamentales

### 1. **Orden de Migración Incorrecto**
- Se intenta migrar datos dependientes antes de que sus dependencias estén completas
- Ejemplo: Migrar sale.order antes de migrar completamente product.product

### 2. **Falta de Validación Previa**
- No se valida que los datos sean correctos antes de migrar
- No se verifica que las dependencias existan

### 3. **Manejo Incorrecto de Campos Relacionales**
- Campos one2many/many2many no se manejan correctamente
- Se intentan migrar como campos simples

### 4. **Falta de Estrategia de Recuperación**
- No hay reintentos
- No hay corrección automática de datos
- No hay migración incremental

### 5. **Mapeo de IDs Incompleto**
- Solo se guardan IDs de registros exitosos
- Si un registro falla, sus dependientes también fallan
- No hay verificación de integridad del mapeo

## Recomendaciones para Plan Mejorado

1. **Migración en Fases Estrictas**
   - Fase 1: Datos base (sin dependencias)
   - Fase 2: Datos maestros (partners, productos)
   - Fase 3: Datos transaccionales (cotizaciones, facturas)
   - Fase 4: Datos relacionados (líneas, variantes)

2. **Validación Previa**
   - Verificar que todos los datos base estén migrados antes de continuar
   - Validar integridad del mapeo de IDs
   - Verificar que las dependencias existan

3. **Manejo Correcto de Campos Relacionales**
   - Migrar one2many/many2many usando comandos Odoo correctos
   - Migrar líneas después de migrar el registro padre
   - Usar formato `[(0, 0, {...})]` para crear relaciones

4. **Estrategia de Reintento**
   - Reintentar registros que fallan con datos mínimos
   - Logging detallado de cada fallo
   - Corrección automática cuando sea posible

5. **Migración de Usuarios Mejorada**
   - Migrar usuarios primero y verificar que todos estén migrados
   - No continuar hasta que usuarios estén completos
   - Manejar usuarios del sistema correctamente

6. **Preservación de Metadatos**
   - Usar `sudo=True` y establecer create_date/write_date durante creación
   - Mapear create_uid/write_uid correctamente
   - Preservar fechas originales

7. **Verificación Post-Migración**
   - Verificar que todos los registros tengan sus relaciones
   - Verificar que las líneas estén migradas
   - Generar reporte de integridad

