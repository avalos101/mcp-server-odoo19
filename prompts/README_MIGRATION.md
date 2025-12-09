# Guía de Migración Automatizada: OmniERP (Odoo 18) → Odoo 19

## Descripción

Este script automatiza la migración completa desde OmniERP (Odoo 18) a una nueva base de datos en Odoo 19, utilizando conexiones SSH y MCP.

## Características

- ✅ Creación automática de base de datos nueva
- ✅ Detección y mapeo de módulos (incluyendo cambios de nombres)
- ✅ Instalación ordenada de módulos respetando dependencias
- ✅ Soporte para módulos Base + Enterprise
- ✅ Migración de datos estructurada
- ✅ Verificación de integridad post-migración
- ✅ Logging completo de todas las operaciones
- ✅ Modo dry-run para pruebas sin cambios

## Requisitos

1. Acceso SSH a ambos servidores (OmniERP y Laia.one)
2. Acceso MCP configurado en ambos servidores
3. Permisos sudo en servidor destino para crear bases de datos
4. Python 3.7+ con módulos: subprocess, xmlrpc.client, ssl, urllib

## Uso

### Modo Dry-Run (Recomendado para pruebas)

```bash
cd prompts
python3 automated_migration_omnierp_to_odoo19.py --dry-run
```

### Migración Completa

```bash
cd prompts
python3 automated_migration_omnierp_to_odoo19.py
```

### Ejecutar Paso Específico

```bash
# Solo crear base de datos
python3 automated_migration_omnierp_to_odoo19.py --step 1

# Solo obtener lista de módulos
python3 automated_migration_omnierp_to_odoo19.py --step 2

# Solo instalar módulos
python3 automated_migration_omnierp_to_odoo19.py --step 3

# Solo migrar datos
python3 automated_migration_omnierp_to_odoo19.py --step 4

# Solo verificar
python3 automated_migration_omnierp_to_odoo19.py --step 5
```

## Pasos de la Migración

### Paso 1: Crear Base de Datos Nueva
- Crea base de datos `omnierp_migrated` en servidor destino
- Inicializa con módulos base de Odoo 19
- Verifica que la creación fue exitosa

### Paso 2: Obtener Lista de Módulos
- Conecta a OmniERP vía SSH o MCP
- Obtiene lista completa de módulos instalados
- Identifica módulos base, enterprise y personalizados
- Mapea nombres de módulos si cambiaron entre versiones

### Paso 3: Instalar Módulos
- Resuelve dependencias entre módulos
- Instala módulos en orden correcto:
  1. Módulos base críticos (base, web, mail)
  2. Módulos en orden definido
  3. Resto de módulos
- Maneja errores y continúa con siguiente módulo

### Paso 4: Migrar Datos
- Migra datos maestros (partners, productos)
- Migra datos transaccionales (ventas, facturas)
- Migra datos de módulos especiales (proyectos, knowledge, helpdesk)
- Mantiene integridad referencial

### Paso 5: Verificar Migración
- Compara conteos de registros entre origen y destino
- Verifica integridad de datos
- Genera reporte de verificación

## Configuración

### Servidor Origen (OmniERP)
```python
SOURCE_SERVER = {
    "url": "https://omnierp.app",
    "db": "omnierp.app",
    "user": "admin@omnierp.app",
    "api_key": "...",
    "ssh_host": "omnierp.app",
    "ssh_user": "diego.avalos"
}
```

### Servidor Destino (Laia.one)
```python
TARGET_SERVER = {
    "url": "https://laia.one",
    "db": "omnierp_migrated",  # Nueva BD
    "user": "admin@laia.one",
    "api_key": "...",
    "ssh_host": "laia.one",
    "ssh_user": "diego.avalos",
    "odoo_bin": "/opt/odoo19/venv/bin/python3 /opt/odoo19/odoo-bin",
    "odoo_config": "/etc/odoo19.conf",
    "odoo_user": "odoo19"
}
```

## Mapeo de Módulos

El script incluye un sistema de mapeo para manejar módulos que cambiaron de nombre entre Odoo 18 y 19:

```python
MODULE_NAME_MAPPING = {
    'old_module_name': 'new_module_name',
    # Agregar más según se identifiquen
}
```

## Módulos Deprecados

Módulos que fueron removidos en Odoo 19:

```python
DEPRECATED_MODULES = [
    # Agregar módulos deprecados
]
```

## Logs y Reportes

- **Log de migración**: `reports/migration_log_YYYYMMDD_HHMMSS.txt`
- **Reporte final**: `reports/migration_report_YYYYMMDD_HHMMSS.txt`

## Manejo de Errores

El script:
- Continúa con siguiente módulo si uno falla
- Registra todos los errores en el log
- Genera reporte de errores al final
- Permite ejecución paso a paso para debugging

## Consideraciones Importantes

1. **Módulos Personalizados**: Requieren revisión manual y posible actualización de código
2. **Módulos Enterprise**: Verificar que estén disponibles en Odoo 19
3. **Cambios de Nombre**: Algunos módulos pueden haber cambiado de nombre
4. **Datos Complejos**: Algunos datos pueden requerir transformación manual
5. **Tiempo**: La migración completa puede tomar varias horas dependiendo del volumen

## Troubleshooting

### Error: "No se pudo conectar SSH"
- Verificar que las llaves SSH están configuradas
- Verificar acceso a servidores

### Error: "Error de autenticación MCP"
- Verificar que las API keys son correctas
- Verificar que MCP está habilitado en ambos servidores

### Error: "Módulo no encontrado"
- Verificar que el módulo existe en Odoo 19
- Verificar mapeo de nombres si cambió

### Error: "Base de datos ya existe"
- El script pregunta si deseas recrearla
- O usar nombre diferente en configuración

## Próximos Pasos Después de la Migración

1. Verificar funcionalidades críticas manualmente
2. Probar creación de nuevos registros
3. Verificar reportes y vistas personalizadas
4. Configurar backups automáticos
5. Capacitar usuarios en nuevas funcionalidades

## Soporte

Para problemas o preguntas:
- Revisar logs en `reports/`
- Ejecutar en modo dry-run primero
- Ejecutar pasos individuales para debugging

