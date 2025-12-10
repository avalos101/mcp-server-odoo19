# Carpeta de Migración de Base de Datos: OmniERP (Odoo 18) → Odoo 19

Esta carpeta contiene todos los archivos relacionados con la migración de **datos de base de datos** desde OmniERP (Odoo 18) hacia Odoo 19.

**Nota:** Esta carpeta es para la migración de datos, no para la migración del módulo MCP (que está en `mcp_server/`).

## Estructura

```
migration-db-18-19/
├── scripts/          # Scripts de migración y análisis
├── reports/          # Reportes y logs de migración
└── docs/             # Documentación del proceso
```

## Contenido

### Scripts (`scripts/`)

**Scripts de Análisis:**
- `analyze_migration_omnierp_to_odoo19.py` - Análisis detallado de origen y destino
- `generate_detailed_migration_plan.py` - Generador de plan de migración
- `check_users_migration.py` - Verificación de usuarios migrados

**Scripts de Migración:**
- `migrate_data_improved.py` - Script principal de migración mejorado
- `migrate_pending_data.py` - Migración de datos pendientes (facturas, tareas)
- `complete_migration.py` - Script completo de migración
- `execute_migration_unattended.py` - Ejecución desatendida
- `install_modules_batch.py` - Instalación de módulos en lotes
- `fix_sale_orders.py` - Corrección de cotizaciones migradas

**Scripts de Reportes:**
- `generate_final_migration_report.py` - Generador de reportes finales
- `final_migration_summary.py` - Resumen de migración

**Documentación de Planes:**
- `PLAN_MIGRACION_DATOS.md` - Plan detallado de migración de datos
- `PLAN_MIGRACION_MEJORADO.md` - Plan mejorado con fases estrictas
- `ANALISIS_FALLOS_MIGRACION.md` - Análisis profundo de fallos
- `VERIFICACION_PREVIA.md` - Verificaciones previas a la migración

### Reportes (`reports/`)

Contiene todos los logs, reportes y estadísticas generados durante las ejecuciones de migración:
- Logs de ejecución
- Reportes finales de migración
- Estadísticas en JSON
- Reportes de verificación

### Documentación (`docs/`)

- `DOCUMENTACION_MIGRACION.md` - Documentación completa del proceso de migración

## Uso

### Para ejecutar una migración nueva:

1. **Revisar el plan mejorado:**
   ```bash
   cat migration-db-18-19/scripts/PLAN_MIGRACION_MEJORADO.md
   ```

2. **Analizar origen y destino:**
   ```bash
   python3 migration-db-18-19/scripts/analyze_migration_omnierp_to_odoo19.py
   ```

3. **Ejecutar migración por fases:**
   ```bash
   python3 migration-db-18-19/scripts/complete_migration.py
   ```

### Para corregir datos migrados:

```bash
python3 migration-db-18-19/scripts/fix_sale_orders.py
```

### Para generar reportes:

```bash
python3 migration-db-18-19/scripts/generate_final_migration_report.py
```

## Notas Importantes

- Todos los scripts están configurados para trabajar con las bases de datos:
  - **Origen:** `omnierp.app` en `https://omnierp.app`
  - **Destino:** `omnierp_migrated` en `https://laia.one`

- Los scripts requieren:
  - Conexión SSH a los servidores
  - Acceso MCP configurado
  - Credenciales de acceso

- Los reportes se generan en `migration-db-18-19/reports/`

## Referencias

- Ver `docs/DOCUMENTACION_MIGRACION.md` para documentación completa
- Ver `scripts/PLAN_MIGRACION_MEJORADO.md` para el plan detallado
- Ver `scripts/ANALISIS_FALLOS_MIGRACION.md` para análisis de problemas

