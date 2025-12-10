# Plan Mejorado de Migración: OmniERP (Odoo 18) → Odoo 19

## Objetivo

Migrar todos los datos desde OmniERP (Odoo 18) a una nueva base de datos en Odoo 19 con:
- **100% de integridad referencial**
- **Todas las relaciones preservadas**
- **Metadatos completos (usuarios, fechas)**
- **Líneas y detalles completos**

## Principios del Plan

1. **Migración en Fases Estrictas**: Cada fase debe completarse 100% antes de continuar
2. **Validación Continua**: Verificar integridad después de cada fase
3. **Manejo Correcto de Relaciones**: Usar comandos Odoo apropiados para one2many/many2many
4. **Preservación de Metadatos**: Usuarios, fechas, historial completo
5. **Estrategia de Recuperación**: Reintentos y correcciones automáticas

---

## FASE 0: Preparación y Validación

### 0.1 Verificación de Entorno Destino
- [ ] Base de datos nueva creada y vacía
- [ ] Odoo 19 instalado y funcionando
- [ ] Módulos base instalados: base, web, mail, portal
- [ ] Módulos de negocio instalados: sale, purchase, stock, account, crm
- [ ] Módulos especiales instalados: project, knowledge, helpdesk
- [ ] Módulo MCP instalado y configurado

### 0.2 Análisis de Origen
- [ ] Contar todos los registros por modelo
- [ ] Identificar dependencias entre modelos
- [ ] Verificar integridad de datos en origen
- [ ] Identificar usuarios activos e inactivos
- [ ] Identificar productos con variantes

### 0.3 Preparación de Scripts
- [ ] Script de migración por fases
- [ ] Script de validación post-fase
- [ ] Script de verificación de integridad
- [ ] Script de generación de reportes

---

## FASE 1: Datos Base (Sin Dependencias)

### 1.1 Unidades de Medida (uom.uom)
**Prioridad:** CRÍTICA  
**Dependencias:** Ninguna  
**Objetivo:** Migrar todas las unidades de medida

**Proceso:**
1. Obtener todas las unidades de origen
2. Verificar cuáles ya existen en destino (por nombre)
3. Crear las que no existen
4. Guardar mapeo de IDs
5. **Validar:** Todas las unidades migradas

**Campos a migrar:**
- name
- category_id (mapear)
- factor
- factor_inv
- rounding
- active

### 1.2 Categorías de Productos (product.category)
**Prioridad:** CRÍTICA  
**Dependencias:** Ninguna (excepto parent_id)  
**Objetivo:** Migrar todas las categorías

**Proceso:**
1. Obtener categorías ordenadas por nivel (sin parent primero)
2. Migrar categorías nivel por nivel
3. Mapear parent_id correctamente
4. **Validar:** Todas las categorías migradas, jerarquía preservada

**Campos a migrar:**
- name
- parent_id (mapear)
- complete_name
- active

### 1.3 Monedas (res.currency)
**Prioridad:** ALTA  
**Dependencias:** Ninguna  
**Objetivo:** Migrar monedas personalizadas

**Proceso:**
1. Obtener monedas de origen
2. Verificar cuáles ya existen en destino
3. Crear solo las personalizadas
4. **Validar:** Monedas necesarias disponibles

---

## FASE 2: Usuarios y Metadatos

### 2.1 Usuarios (res.users)
**Prioridad:** CRÍTICA  
**Dependencias:** res.partner (para partner_id)  
**Objetivo:** Migrar TODOS los usuarios (activos e inactivos)

**Proceso:**
1. **Primero:** Crear partners básicos para usuarios (si no existen)
2. Obtener todos los usuarios de origen
3. Para cada usuario:
   - Verificar si ya existe (por login)
   - Si no existe, crear con:
     - login
     - name
     - active
     - partner_id (mapear)
     - password temporal (cambiar después)
   - Mapear grupos de seguridad (si es posible)
4. Mapear usuarios del sistema a usuarios existentes en destino
5. **Validar:** 100% de usuarios migrados, mapeo completo

**Campos a migrar:**
- login
- name
- active
- partner_id (mapear)
- email
- groups_id (mapear grupos)

**Nota:** Los usuarios son CRÍTICOS porque se usan para create_uid/write_uid

### 2.2 Grupos de Usuarios (res.groups)
**Prioridad:** MEDIA  
**Dependencias:** Ninguna  
**Objetivo:** Verificar que grupos necesarios existan

**Proceso:**
1. Obtener grupos de usuarios de origen
2. Verificar que existan en destino
3. Crear solo los personalizados si es necesario
4. **Validar:** Grupos necesarios disponibles

---

## FASE 3: Datos Maestros

### 3.1 Partners (res.partner)
**Prioridad:** CRÍTICA  
**Dependencias:** res.users (para create_uid/write_uid)  
**Objetivo:** Migrar todos los partners

**Proceso:**
1. Obtener todos los partners de origen
2. Ordenar por jerarquía (sin parent primero)
3. Para cada partner:
   - Mapear parent_id si existe
   - Mapear create_uid/write_uid usando user_mapping
   - Crear con todos los campos
4. **Validar:** 100% de partners migrados, jerarquía preservada

**Campos a migrar:**
- name
- parent_id (mapear)
- is_company
- customer_rank
- supplier_rank
- email
- phone
- mobile
- street, street2, city, state_id, country_id, zip
- vat
- create_uid (mapear)
- write_uid (mapear)

### 3.2 Productos Template (product.template)
**Prioridad:** CRÍTICA  
**Dependencias:** product.category, uom.uom  
**Objetivo:** Migrar todos los productos template

**Proceso:**
1. Obtener todos los productos template de origen
2. Para cada producto:
   - Mapear categ_id
   - Mapear uom_id, uom_po_id
   - Crear producto template
   - Guardar mapeo
3. **Validar:** 100% de productos template migrados

**Campos a migrar:**
- name
- categ_id (mapear)
- list_price
- standard_price
- uom_id (mapear)
- uom_po_id (mapear)
- type
- sale_ok
- purchase_ok
- active
- default_code
- barcode
- create_uid (mapear)
- write_uid (mapear)

### 3.3 Productos Variantes (product.product)
**Prioridad:** CRÍTICA  
**Dependencias:** product.template  
**Objetivo:** Migrar todas las variantes

**Proceso:**
1. Obtener todos los productos variantes de origen
2. Para cada variante:
   - Mapear product_tmpl_id
   - Crear variante
   - Guardar mapeo
3. **Validar:** 100% de variantes migradas, todas relacionadas a templates

**Campos a migrar:**
- product_tmpl_id (mapear)
- default_code
- barcode
- active
- create_uid (mapear)
- write_uid (mapear)

---

## FASE 4: Datos Transaccionales - Parte 1

### 4.1 Leads (crm.lead)
**Prioridad:** ALTA  
**Dependencias:** res.partner, res.users  
**Objetivo:** Migrar todos los leads

**Proceso:**
1. Obtener todos los leads de origen
2. Para cada lead:
   - Mapear partner_id
   - Mapear user_id (comercial)
   - Mapear stage_id (si existe)
   - Crear lead
3. **Validar:** 100% de leads migrados, relaciones correctas

**Campos a migrar:**
- name
- partner_id (mapear)
- user_id (mapear)
- stage_id (mapear)
- probability
- expected_revenue
- email_from
- phone
- active
- create_uid (mapear)
- write_uid (mapear)

### 4.2 Proyectos (project.project)
**Prioridad:** ALTA  
**Dependencias:** res.partner, res.users  
**Objetivo:** Migrar todos los proyectos

**Proceso:**
1. Obtener todos los proyectos de origen
2. Para cada proyecto:
   - Mapear partner_id
   - Mapear user_id
   - Crear proyecto
   - Guardar mapeo
3. **Validar:** 100% de proyectos migrados

**Campos a migrar:**
- name
- partner_id (mapear)
- user_id (mapear)
- active
- create_uid (mapear)
- write_uid (mapear)

---

## FASE 5: Cotizaciones y Órdenes (Con Líneas)

### 5.1 Cotizaciones/Órdenes (sale.order) - SIN LÍNEAS
**Prioridad:** CRÍTICA  
**Dependencias:** res.partner, res.users, product.product  
**Objetivo:** Crear estructura de cotizaciones

**Proceso:**
1. Obtener todas las cotizaciones de origen
2. Para cada cotización:
   - Mapear partner_id
   - Mapear user_id (comercial) - **CRÍTICO**
   - Establecer date_order correctamente
   - Crear cotización SIN líneas aún
   - Guardar mapeo
3. **Validar:** 100% de cotizaciones creadas, con comercial y fecha

**Campos a migrar:**
- name
- partner_id (mapear)
- user_id (mapear) - **CRÍTICO: Comercial**
- date_order - **CRÍTICO: Fecha correcta**
- state
- amount_total (se recalculará con líneas)
- create_uid (mapear)
- write_uid (mapear)

**Nota:** NO migrar order_line aún

### 5.2 Líneas de Cotización (sale.order.line)
**Prioridad:** CRÍTICA  
**Dependencias:** sale.order, product.product  
**Objetivo:** Migrar todas las líneas con datos completos

**Proceso:**
1. Para cada cotización migrada:
   - Obtener líneas de origen usando order_id original
   - Para cada línea:
     - Mapear order_id (nuevo ID)
     - Mapear product_id
     - Mapear product_uom
     - Crear línea con:
       - name (descripción completa)
       - product_uom_qty (cantidad)
       - price_unit (precio unitario)
       - discount (descuento)
       - price_subtotal (se calculará automáticamente)
2. **Validar:** Todas las cotizaciones tienen sus líneas, cantidades y precios correctos

**Campos a migrar:**
- order_id (mapear)
- product_id (mapear)
- name - **CRÍTICO: Descripción completa**
- product_uom_qty - **CRÍTICO: Cantidad**
- price_unit - **CRÍTICO: Precio**
- product_uom (mapear)
- discount
- sequence

**Comando Odoo:**
```python
# Crear línea usando write con comandos
target_models.execute_kw(
    db, uid, password,
    'sale.order', 'write',
    [[order_id], {
        'order_line': [(0, 0, line_data)]
    }]
)
```

---

## FASE 6: Facturas

### 6.1 Facturas (account.move)
**Prioridad:** ALTA  
**Dependencias:** res.partner, sale.order  
**Objetivo:** Migrar todas las facturas

**Proceso:**
1. Obtener todas las facturas de origen
2. Verificar que todos los partners estén migrados
3. Para cada factura:
   - Mapear partner_id
   - Mapear invoice_origin (sale.order) si existe
   - Crear factura en estado 'draft'
   - Guardar mapeo
4. **Validar:** 100% de facturas migradas

**Campos a migrar:**
- name
- partner_id (mapear)
- move_type
- invoice_date
- invoice_origin (mapear sale.order)
- state (crear como 'draft')
- amount_total
- create_uid (mapear)
- write_uid (mapear)

### 6.2 Líneas de Factura (account.move.line)
**Prioridad:** ALTA  
**Dependencias:** account.move, product.product  
**Objetivo:** Migrar líneas de factura

**Proceso:**
1. Para cada factura migrada:
   - Obtener líneas de origen
   - Crear líneas con productos, cantidades, precios
2. **Validar:** Todas las facturas tienen sus líneas

---

## FASE 7: Proyectos y Tareas

### 7.1 Tareas de Proyecto (project.task)
**Prioridad:** MEDIA  
**Dependencias:** project.project, res.users  
**Objetivo:** Migrar todas las tareas

**Proceso:**
1. Obtener todas las tareas de origen
2. Verificar que todos los proyectos estén migrados
3. Para cada tarea:
   - Mapear project_id
   - Mapear partner_id si existe
   - Mapear user_ids (many2many) - **CORRECTO para Odoo 19**
   - Crear tarea
4. **Validar:** 100% de tareas migradas

**Campos a migrar:**
- name
- project_id (mapear)
- partner_id (mapear)
- user_ids (mapear) - **Many2many en Odoo 19**
- stage_id (mapear)
- description
- active
- create_uid (mapear)
- write_uid (mapear)

**Formato Odoo 19:**
```python
data['user_ids'] = [(6, 0, [user_id1, user_id2, ...])]  # Many2many
```

---

## FASE 8: Knowledge y Helpdesk

### 8.1 Artículos de Knowledge (knowledge.article)
**Prioridad:** MEDIA  
**Dependencias:** res.users  
**Objetivo:** Migrar artículos

**Proceso:**
1. Obtener todos los artículos de origen
2. Migrar con jerarquía (parent_id)
3. **Validar:** Artículos migrados

### 8.2 Tickets de Helpdesk (helpdesk.ticket)
**Prioridad:** MEDIA  
**Dependencias:** res.partner, res.users  
**Objetivo:** Migrar tickets

**Proceso:**
1. Obtener todos los tickets de origen
2. Mapear partner_id, user_id
3. Migrar tickets
4. **Validar:** Tickets migrados

---

## FASE 9: Verificación y Corrección Final

### 9.1 Verificación de Integridad
- [ ] Verificar que todas las cotizaciones tengan líneas
- [ ] Verificar que todas las cotizaciones tengan comercial
- [ ] Verificar que todas las cotizaciones tengan fecha correcta
- [ ] Verificar que todas las facturas tengan líneas
- [ ] Verificar que todas las tareas tengan proyecto
- [ ] Verificar mapeo de IDs completo

### 9.2 Corrección de Datos Faltantes
- [ ] Corregir cotizaciones sin líneas
- [ ] Corregir cotizaciones sin comercial
- [ ] Corregir fechas incorrectas
- [ ] Corregir relaciones rotas

### 9.3 Generación de Reporte Final
- [ ] Comparar conteos origen vs destino
- [ ] Generar reporte de integridad
- [ ] Listar registros no migrados (si los hay)
- [ ] Documentar problemas encontrados

---

## Scripts Requeridos

### 1. `migrate_phase_base.py`
Migra datos base (uom, categorías, monedas)

### 2. `migrate_phase_users.py`
Migra usuarios y grupos

### 3. `migrate_phase_masters.py`
Migra partners y productos

### 4. `migrate_phase_transactions.py`
Migra cotizaciones, facturas, leads

### 5. `migrate_phase_lines.py`
Migra líneas de cotización y factura

### 6. `migrate_phase_projects.py`
Migra proyectos y tareas

### 7. `migrate_phase_knowledge.py`
Migra knowledge y helpdesk

### 8. `validate_migration.py`
Valida integridad después de cada fase

### 9. `fix_missing_data.py`
Corrige datos faltantes identificados

---

## Validaciones por Fase

Cada fase debe tener validaciones que verifiquen:

1. **Conteo:** Todos los registros migrados
2. **Integridad:** Todas las relaciones correctas
3. **Metadatos:** Usuarios y fechas correctas
4. **Datos:** Campos completos y correctos

**No continuar a la siguiente fase hasta que la actual esté 100% completa.**

---

## Manejo de Errores

### Estrategia de Reintento
1. **Primer intento:** Con todos los campos
2. **Segundo intento:** Con campos mínimos requeridos
3. **Tercer intento:** Con datos por defecto
4. **Registro:** Log detallado de cada fallo

### Corrección Automática
- Mapear a valores por defecto cuando sea posible
- Crear registros faltantes si son necesarios
- Saltar solo si es absolutamente necesario

---

## Métricas de Éxito

- **100% de usuarios migrados**
- **100% de partners migrados**
- **100% de productos migrados**
- **100% de cotizaciones con líneas completas**
- **100% de cotizaciones con comercial asignado**
- **100% de cotizaciones con fecha correcta**
- **100% de facturas migradas**
- **100% de proyectos y tareas migrados**
- **0% de relaciones rotas**

---

## Notas Importantes

1. **Orden es crítico:** No saltar fases
2. **Validación continua:** Verificar después de cada fase
3. **Mapeo completo:** Guardar todos los mapeos de IDs
4. **Metadatos:** Preservar usuarios y fechas
5. **Relaciones:** Usar comandos Odoo correctos para one2many/many2many
6. **Líneas separadas:** Migrar líneas después del registro padre

---

**Este plan debe ejecutarse en una base de datos nueva y vacía, creada específicamente para esta migración.**

