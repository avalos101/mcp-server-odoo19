# Plan de Migración de Datos: OmniERP → Odoo 19

## Datos a Migrar

### 1. Datos Maestros (Base)
- **res.partner** (Clientes/Contactos)
  - Partners activos
  - Relaciones entre partners
  - Direcciones
  - Categorías de partners

### 2. Productos y Servicios
- **product.template** (Plantillas de productos)
- **product.product** (Variantes de productos)
- **product.category** (Categorías)
- **uom.uom** (Unidades de medida) - si no existen

### 3. CRM
- **crm.lead** (Leads/Oportunidades)
  - Relaciones con partners
  - Etapas y estados
  - Actividades

### 4. Ventas
- **sale.order** (Cotizaciones/Órdenes de venta)
  - **sale.order.line** (Líneas de cotización)
  - Estados y etapas
  - Relaciones con partners y productos

### 5. Contabilidad
- **account.move** (Facturas)
  - **account.move.line** (Líneas de factura)
  - Estados de facturación
  - Relaciones con partners y órdenes de venta

### 6. Proyectos
- **project.project** (Proyectos)
  - **project.task** (Tareas)
  - Estados y etapas
  - Asignaciones
  - Relaciones con partners y ventas

### 7. Knowledge (si aplica)
- **knowledge.article** (Artículos)
  - Contenido y estructura
  - Permisos

### 8. Helpdesk (si aplica)
- **helpdesk.ticket** (Tickets)
  - Estados y etapas
  - Asignaciones
  - Relaciones con partners

## Métodos de Migración

### Opción 1: MCP (Model Context Protocol) - RECOMENDADO
**Ventajas:**
- Usa la API oficial de Odoo
- Maneja automáticamente relaciones y validaciones
- Respeta reglas de negocio
- Más seguro

**Desventajas:**
- Más lento para grandes volúmenes
- Requiere que MCP esté habilitado en ambos servidores

### Opción 2: PostgreSQL Directo (pg_dump/pg_restore)
**Ventajas:**
- Muy rápido para grandes volúmenes
- Migra datos en bloque

**Desventajas:**
- Puede causar problemas de integridad
- No respeta reglas de negocio de Odoo
- Requiere transformaciones manuales
- Riesgo de errores por cambios de esquema

### Opción 3: Híbrido
- MCP para datos maestros y relaciones complejas
- PostgreSQL para datos masivos simples

## Orden de Migración (Importante)

1. **Datos base sin dependencias:**
   - Unidades de medida (uom.uom)
   - Categorías de productos (product.category)
   - Categorías de partners (res.partner.category)

2. **Datos maestros:**
   - Partners (res.partner) - Base para todo lo demás

3. **Productos:**
   - Product templates
   - Product variants

4. **CRM:**
   - Leads (dependen de partners)

5. **Ventas:**
   - Cotizaciones (dependen de partners y productos)
   - Líneas de cotización

6. **Contabilidad:**
   - Facturas (dependen de partners, productos, órdenes)
   - Líneas de factura

7. **Proyectos:**
   - Proyectos (pueden depender de partners, ventas)
   - Tareas (dependen de proyectos)

8. **Knowledge y Helpdesk:**
   - Artículos
   - Tickets

## Consideraciones Importantes

### Cambios entre Odoo 18 y 19
- Algunos campos pueden haber cambiado de nombre
- Algunos campos pueden haber sido deprecados
- Nuevos campos requeridos
- Cambios en relaciones many2one

### Validaciones Necesarias
- Verificar que partners existan antes de crear órdenes
- Verificar que productos existan antes de crear líneas
- Mantener integridad referencial
- Manejar errores y continuar con siguiente registro

### Transformaciones Requeridas
- IDs de registros relacionados (partners, productos)
- Fechas y formatos
- Estados y etapas (pueden tener diferentes valores)
- Campos calculados (no se migran, se recalculan)

## Permisos Necesarios

### En Servidor Origen (OmniERP)
- ✅ Lectura vía MCP (ya configurado)
- ✅ Lectura vía SSH/PostgreSQL (ya disponible)

### En Servidor Destino (Laia.one)
- ✅ Escritura vía MCP (necesita verificación)
- ✅ Modelos habilitados en MCP (necesita verificación)
- ⚠️ Permisos de creación/escritura en modelos

## Verificaciones Previas Necesarias

1. **MCP en destino:**
   - ¿Está funcionando?
   - ¿Qué modelos están habilitados?
   - ¿Tengo permisos de escritura?

2. **Modelos habilitados:**
   - res.partner
   - product.template
   - product.product
   - crm.lead
   - sale.order
   - account.move
   - project.project
   - project.task
   - knowledge.article
   - helpdesk.ticket

3. **Permisos de usuario:**
   - ¿El usuario admin@laia.one tiene permisos para crear registros?
   - ¿Necesito habilitar más modelos en MCP?

## Estrategia Propuesta

1. **Fase 1: Verificación**
   - Verificar MCP en destino
   - Habilitar modelos necesarios
   - Verificar permisos

2. **Fase 2: Migración de datos base**
   - Categorías
   - Unidades de medida
   - Configuraciones básicas

3. **Fase 3: Migración de datos maestros**
   - Partners (con mapeo de IDs)

4. **Fase 4: Migración de productos**
   - Templates y variants

5. **Fase 5: Migración de datos transaccionales**
   - Leads
   - Cotizaciones
   - Facturas

6. **Fase 6: Migración de proyectos**
   - Proyectos y tareas

7. **Fase 7: Migración de Knowledge y Helpdesk**

8. **Fase 8: Verificación**
   - Conteos
   - Integridad
   - Reporte final

## Riesgos y Mitigaciones

### Riesgo 1: MCP no disponible en destino
**Mitigación:** Habilitar MCP y modelos antes de migrar

### Riesgo 2: Permisos insuficientes
**Mitigación:** Verificar y configurar permisos antes de migrar

### Riesgo 3: Errores de integridad
**Mitigación:** Migrar en orden correcto, validar antes de crear

### Riesgo 4: Timeouts en grandes volúmenes
**Mitigación:** Migrar en lotes, con reintentos

### Riesgo 5: Cambios de esquema entre versiones
**Mitigación:** Mapear campos, transformar datos cuando sea necesario

