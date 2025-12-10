# Verificación Previa para Migración de Datos

## Estado Actual Verificado

### ✅ Disponible
1. **SSH acceso:**
   - Origen (OmniERP): ✓ Funcionando
   - Destino (Laia.one): ✓ Funcionando

2. **MCP en Origen:**
   - ✓ Conectado y funcionando
   - ✓ UID: 2 (admin@omnierp.app)
   - ✓ Puedo leer datos

3. **Base de datos destino:**
   - ✓ Creada: omnierp_migrated
   - ✓ Inicializada con módulos base
   - ✓ Módulos principales instalados

4. **Modelos habilitados en MCP destino:**
   - ✓ 10 modelos habilitados
   - ⚠️ Necesito verificar permisos de escritura

### ⚠️ Pendiente de Verificación

1. **MCP en Destino:**
   - ✗ No conectado actualmente
   - ⚠️ Necesito habilitar/verificar MCP
   - ⚠️ Necesito verificar permisos de escritura

2. **Permisos de escritura:**
   - ⚠️ ¿Puedo crear registros vía MCP?
   - ⚠️ ¿Qué modelos tienen allow_create=true?

3. **Servicio Odoo:**
   - ⚠️ ¿Está corriendo?
   - ⚠️ ¿Necesito reiniciarlo?

## Lo que NECESITO confirmar antes de continuar:

### 1. MCP en Destino
**Pregunta:** ¿Puedo habilitar/verificar MCP en la base de datos `omnierp_migrated`?

**Acciones necesarias:**
- Verificar que el módulo mcp_server esté instalado
- Verificar que MCP esté habilitado en configuración
- Verificar que los modelos necesarios estén habilitados con permisos de escritura

**Comandos que necesito ejecutar (con permisos):**
```bash
# Verificar módulo instalado
sudo -u postgres psql -d omnierp_migrated -c "SELECT name FROM ir_module_module WHERE name='mcp_server' AND state='installed';"

# Habilitar MCP si no está
sudo -u postgres psql -d omnierp_migrated -c "INSERT INTO ir_config_parameter (key, value) VALUES ('mcp_server.enabled', 'True') ON CONFLICT (key) DO UPDATE SET value = 'True';"

# Habilitar modelos con permisos de escritura
sudo -u postgres psql -d omnierp_migrated -c "UPDATE mcp_enabled_model SET allow_create=true, allow_write=true WHERE model_name IN ('res.partner', 'product.template', 'product.product', 'crm.lead', 'sale.order', 'account.move', 'project.project', 'project.task');"
```

### 2. Permisos de Usuario
**Pregunta:** ¿El usuario `admin@laia.one` tiene permisos para crear registros en los modelos necesarios?

**Verificación necesaria:**
- Probar creación de un registro de prueba vía MCP
- Verificar grupos de seguridad del usuario

### 3. Reinicio de Servicio (si es necesario)
**Pregunta:** ¿Necesito reiniciar el servicio Odoo19 para que los cambios de MCP tomen efecto?

**Comando que podría necesitar:**
```bash
sudo systemctl restart odoo19
```

## Plan de Acción Propuesto

### Fase 1: Preparación (SIN migrar datos aún)
1. Verificar módulo mcp_server instalado
2. Habilitar MCP en configuración
3. Habilitar modelos necesarios con permisos de escritura
4. Reiniciar servicio si es necesario
5. Verificar conexión MCP en destino
6. Probar creación de registro de prueba

### Fase 2: Migración (solo después de Fase 1 exitosa)
1. Migrar datos base (categorías, unidades)
2. Migrar partners
3. Migrar productos
4. Migrar leads
5. Migrar cotizaciones
6. Migrar facturas
7. Migrar proyectos
8. Migrar knowledge y helpdesk

## Confirmación Necesaria

**ANTES de ejecutar comandos que requieren permisos, necesito confirmar:**

1. ✅ ¿Puedo ejecutar comandos SQL vía SSH en el servidor destino?
2. ✅ ¿Puedo reiniciar el servicio Odoo19 si es necesario?
3. ✅ ¿Hay alguna restricción de seguridad que deba conocer?

**Si confirmas, procederé con:**
1. Verificación y habilitación de MCP
2. Configuración de permisos
3. Prueba de conexión
4. Inicio de migración de datos

