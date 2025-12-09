#!/usr/bin/env python3
"""
Generación de Plan Detallado de Migración: OmniERP (Odoo 18) → Odoo 19
Ubicado en: prompts/generate_detailed_migration_plan.py

Este script genera un plan detallado de migración basado en el análisis previo.
"""

from datetime import datetime
from pathlib import Path

# Datos del análisis
SOURCE_DATA = {
    "name": "OmniERP",
    "url": "https://omnierp.app",
    "db": "omnierp.app",
    "version": "Odoo 18.0",
    "mcp_version": "18.0.1.0.2",
    "database_size": "375 MB",
    "total_modules": 314,
    "custom_modules": 0,
    "data": {
        "partners": 7626,
        "products": 830,
        "sales_orders": 1986,
        "invoices": 36,
        "leads": 3213,
        "projects": 18,
        "tasks": 317
    }
}

TARGET_DATA = {
    "name": "Laia.one",
    "url": "https://laia.one",
    "db": "admin-laia",
    "version": "Odoo 19.0",
    "mcp_version": "19.0.1.0.0",
    "database_size": "154 MB",
    "total_modules": 197,
    "custom_modules": 0,
    "data": {
        "partners": 8,
        "products": 15,
        "sales_orders": 0,
        "invoices": 1,
        "leads": 0,
        "projects": 0,
        "tasks": 0
    }
}


def generate_detailed_plan():
    """Genera plan detallado de migración"""
    
    report_path = Path(__file__).parent.parent / "reports" / f"detailed_migration_plan_omnierp_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    report_path.parent.mkdir(exist_ok=True)
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("="*80 + "\n")
        f.write("PLAN DETALLADO DE MIGRACIÓN: OMNIIRP (Odoo 18) → ODOO 19\n")
        f.write("="*80 + "\n")
        f.write(f"Fecha de generación: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Resumen ejecutivo
        f.write("RESUMEN EJECUTIVO\n")
        f.write("-"*80 + "\n")
        f.write(f"Origen: {SOURCE_DATA['name']} ({SOURCE_DATA['version']})\n")
        f.write(f"Destino: {TARGET_DATA['name']} ({TARGET_DATA['version']})\n")
        f.write(f"Tamaño base de datos origen: {SOURCE_DATA['database_size']}\n")
        f.write(f"Total de registros a migrar: ~{sum(SOURCE_DATA['data'].values()):,}\n")
        f.write(f"Módulos instalados en origen: {SOURCE_DATA['total_modules']}\n")
        f.write(f"Módulos instalados en destino: {TARGET_DATA['total_modules']}\n")
        f.write(f"Diferencia de módulos: {SOURCE_DATA['total_modules'] - TARGET_DATA['total_modules']}\n\n")
        
        # Análisis de datos
        f.write("ANÁLISIS DE DATOS A MIGRAR\n")
        f.write("-"*80 + "\n")
        f.write(f"{'Modelo':<30} {'Registros Origen':<20} {'Registros Destino':<20} {'Diferencia':<15}\n")
        f.write("-"*80 + "\n")
        
        total_to_migrate = 0
        for key, source_count in SOURCE_DATA['data'].items():
            target_count = TARGET_DATA['data'].get(key, 0)
            difference = source_count - target_count
            if difference > 0:
                total_to_migrate += difference
            f.write(f"{key:<30} {source_count:<20,} {target_count:<20,} {difference:<15,}\n")
        
        f.write(f"\nTotal de registros a migrar: {total_to_migrate:,}\n\n")
        
        # Análisis de módulos
        f.write("ANÁLISIS DE MÓDULOS\n")
        f.write("-"*80 + "\n")
        f.write(f"Módulos en origen: {SOURCE_DATA['total_modules']}\n")
        f.write(f"Módulos en destino: {TARGET_DATA['total_modules']}\n")
        f.write(f"Módulos faltantes en destino: {SOURCE_DATA['total_modules'] - TARGET_DATA['total_modules']}\n")
        f.write(f"Módulos personalizados en origen: {SOURCE_DATA['custom_modules']}\n")
        f.write("\n⚠️  IMPORTANTE: Se requiere verificar compatibilidad de todos los módulos con Odoo 19\n")
        f.write("   Algunos módulos de Odoo 18 pueden requerir actualización o no estar disponibles en Odoo 19\n\n")
        
        # Plan de migración detallado
        f.write("PLAN DE MIGRACIÓN DETALLADO\n")
        f.write("="*80 + "\n\n")
        
        # Fase 1: Preparación
        f.write("FASE 1: PREPARACIÓN Y ANÁLISIS\n")
        f.write("-"*80 + "\n")
        f.write("1.1. Backup y Verificación\n")
        f.write("   [ ] Crear backup completo de base de datos OmniERP\n")
        f.write("   [ ] Verificar integridad del backup\n")
        f.write("   [ ] Documentar tamaño exacto: ~375 MB\n")
        f.write("   [ ] Verificar espacio disponible en servidor destino (mínimo 1 GB)\n")
        f.write("   [ ] Crear punto de restauración en servidor destino\n\n")
        
        f.write("1.2. Análisis de Módulos\n")
        f.write("   [ ] Exportar lista completa de módulos instalados en origen\n")
        f.write("   [ ] Verificar disponibilidad de cada módulo para Odoo 19\n")
        f.write("   [ ] Identificar módulos que requieren actualización\n")
        f.write("   [ ] Identificar módulos obsoletos o no compatibles\n")
        f.write("   [ ] Crear lista de módulos a instalar en destino\n")
        f.write("   [ ] Verificar dependencias entre módulos\n\n")
        
        f.write("1.3. Análisis de Personalizaciones\n")
        f.write("   [ ] Documentar vistas personalizadas\n")
        f.write("   [ ] Documentar reportes personalizados\n")
        f.write("   [ ] Documentar workflows y automatizaciones\n")
        f.write("   [ ] Documentar campos personalizados\n")
        f.write("   [ ] Documentar reglas de negocio personalizadas\n\n")
        
        f.write("1.4. Preparación del Entorno Destino\n")
        f.write("   [ ] Verificar que Odoo 19 está correctamente instalado\n")
        f.write("   [ ] Crear nueva base de datos o limpiar base existente\n")
        f.write("   [ ] Configurar parámetros de sistema\n")
        f.write("   [ ] Preparar scripts de migración\n\n")
        
        # Fase 2: Instalación de módulos
        f.write("FASE 2: INSTALACIÓN DE MÓDULOS BASE\n")
        f.write("-"*80 + "\n")
        f.write("2.1. Módulos Base\n")
        f.write("   [ ] Instalar módulos base de Odoo 19\n")
        f.write("   [ ] Configurar empresa y datos básicos\n")
        f.write("   [ ] Configurar moneda, idioma, zona horaria\n\n")
        
        f.write("2.2. Módulos Estándar\n")
        f.write("   [ ] Instalar módulos de ventas (sale)\n")
        f.write("   [ ] Instalar módulos de compras (purchase)\n")
        f.write("   [ ] Instalar módulos de inventario (stock)\n")
        f.write("   [ ] Instalar módulos de contabilidad (account)\n")
        f.write("   [ ] Instalar módulos de CRM (crm)\n")
        f.write("   [ ] Instalar módulos de proyectos (project)\n")
        f.write("   [ ] Instalar otros módulos necesarios según análisis\n")
        f.write("   [ ] Verificar que todos los módulos se instalaron correctamente\n\n")
        
        # Fase 3: Migración de datos
        f.write("FASE 3: MIGRACIÓN DE DATOS\n")
        f.write("-"*80 + "\n")
        f.write("3.1. Datos Maestros (Orden crítico)\n")
        f.write("   [ ] Migrar monedas y configuraciones financieras\n")
        f.write("   [ ] Migrar unidades de medida\n")
        f.write("   [ ] Migrar categorías de productos\n")
        f.write("   [ ] Migrar productos ({:,} registros)\n".format(SOURCE_DATA['data']['products']))
        f.write("   [ ] Migrar partners ({:,} registros)\n".format(SOURCE_DATA['data']['partners']))
        f.write("   [ ] Migrar usuarios y grupos\n")
        f.write("   [ ] Migrar configuraciones de empresa\n\n")
        
        f.write("3.2. Datos Transaccionales\n")
        f.write("   [ ] Migrar órdenes de venta ({:,} registros)\n".format(SOURCE_DATA['data']['sales_orders']))
        f.write("   [ ] Migrar facturas ({:,} registros)\n".format(SOURCE_DATA['data']['invoices']))
        f.write("   [ ] Migrar líneas de factura\n")
        f.write("   [ ] Migrar movimientos de inventario\n")
        f.write("   [ ] Migrar pagos y transacciones bancarias\n\n")
        
        f.write("3.3. Datos de CRM y Proyectos\n")
        f.write("   [ ] Migrar leads ({:,} registros)\n".format(SOURCE_DATA['data']['leads']))
        f.write("   [ ] Migrar oportunidades\n")
        f.write("   [ ] Migrar proyectos ({:,} registros)\n".format(SOURCE_DATA['data']['projects']))
        f.write("   [ ] Migrar tareas ({:,} registros)\n".format(SOURCE_DATA['data']['tasks']))
        f.write("   [ ] Migrar historial de comunicaciones\n\n")
        
        f.write("3.4. Documentos y Adjuntos\n")
        f.write("   [ ] Migrar documentos adjuntos\n")
        f.write("   [ ] Migrar mensajes y notas\n")
        f.write("   [ ] Verificar integridad de archivos\n\n")
        
        # Fase 4: Personalizaciones
        f.write("FASE 4: APLICACIÓN DE PERSONALIZACIONES\n")
        f.write("-"*80 + "\n")
        f.write("4.1. Vistas y Reportes\n")
        f.write("   [ ] Aplicar vistas personalizadas\n")
        f.write("   [ ] Verificar compatibilidad con Odoo 19\n")
        f.write("   [ ] Ajustar vistas que requieran cambios\n")
        f.write("   [ ] Aplicar reportes personalizados\n")
        f.write("   [ ] Probar generación de reportes\n\n")
        
        f.write("4.2. Configuraciones\n")
        f.write("   [ ] Aplicar configuraciones personalizadas\n")
        f.write("   [ ] Configurar workflows\n")
        f.write("   [ ] Configurar automatizaciones\n")
        f.write("   [ ] Configurar reglas de negocio\n\n")
        
        # Fase 5: Verificación
        f.write("FASE 5: VERIFICACIÓN Y PRUEBAS\n")
        f.write("-"*80 + "\n")
        f.write("5.1. Verificación de Integridad\n")
        f.write("   [ ] Verificar conteo de registros por modelo\n")
        f.write("   [ ] Verificar relaciones entre registros\n")
        f.write("   [ ] Verificar integridad referencial\n")
        f.write("   [ ] Verificar que no hay registros huérfanos\n\n")
        
        f.write("5.2. Pruebas Funcionales\n")
        f.write("   [ ] Probar creación de órdenes de venta\n")
        f.write("   [ ] Probar generación de facturas\n")
        f.write("   [ ] Probar movimientos de inventario\n")
        f.write("   [ ] Probar funcionalidades de CRM\n")
        f.write("   [ ] Probar funcionalidades de proyectos\n")
        f.write("   [ ] Probar reportes y vistas\n")
        f.write("   [ ] Probar acceso de usuarios\n\n")
        
        f.write("5.3. Pruebas de Rendimiento\n")
        f.write("   [ ] Verificar tiempos de carga\n")
        f.write("   [ ] Verificar rendimiento de consultas\n")
        f.write("   [ ] Optimizar índices si es necesario\n\n")
        
        # Fase 6: Puesta en producción
        f.write("FASE 6: PUESTA EN PRODUCCIÓN\n")
        f.write("-"*80 + "\n")
        f.write("6.1. Preparación Final\n")
        f.write("   [ ] Configurar backups automáticos\n")
        f.write("   [ ] Configurar monitoreo\n")
        f.write("   [ ] Documentar cambios y configuraciones\n")
        f.write("   [ ] Preparar documentación para usuarios\n\n")
        
        f.write("6.2. Migración de Usuarios\n")
        f.write("   [ ] Notificar a usuarios sobre la migración\n")
        f.write("   [ ] Capacitar usuarios en nuevas funcionalidades\n")
        f.write("   [ ] Proporcionar acceso a usuarios\n")
        f.write("   [ ] Configurar permisos y grupos\n\n")
        
        f.write("6.3. Go-Live\n")
        f.write("   [ ] Ejecutar migración final\n")
        f.write("   [ ] Verificar que todo funciona correctamente\n")
        f.write("   [ ] Monitorear sistema durante primeras 24 horas\n")
        f.write("   [ ] Resolver problemas inmediatos\n\n")
        
        # Riesgos y consideraciones
        f.write("RIESGOS Y CONSIDERACIONES\n")
        f.write("="*80 + "\n")
        f.write("1. Compatibilidad de Módulos\n")
        f.write("   ⚠️  {SOURCE_DATA['total_modules'] - TARGET_DATA['total_modules']} módulos pueden no estar disponibles en Odoo 19\n")
        f.write("   ⚠️  Algunos módulos pueden requerir actualización\n")
        f.write("   ⚠️  Módulos personalizados pueden requerir reescritura\n\n")
        
        f.write("2. Cambios en Odoo 19\n")
        f.write("   ⚠️  Cambios en estructura de base de datos\n")
        f.write("   ⚠️  Cambios en API y métodos\n")
        f.write("   ⚠️  Cambios en vistas y reportes\n")
        f.write("   ⚠️  Cambios en workflows y automatizaciones\n\n")
        
        f.write("3. Volumen de Datos\n")
        f.write("   ⚠️  {:,} registros a migrar requiere tiempo considerable\n".format(total_to_migrate))
        f.write("   ⚠️  Posible downtime durante migración\n")
        f.write("   ⚠️  Necesidad de validación exhaustiva\n\n")
        
        f.write("4. Personalizaciones\n")
        f.write("   ⚠️  Vistas personalizadas pueden requerir ajustes\n")
        f.write("   ⚠️  Reportes personalizados pueden requerir actualización\n")
        f.write("   ⚠️  Workflows pueden necesitar reconfiguración\n\n")
        
        # Estimaciones
        f.write("ESTIMACIONES DE TIEMPO\n")
        f.write("="*80 + "\n")
        f.write("Fase 1 (Preparación): 4-8 horas\n")
        f.write("Fase 2 (Instalación módulos): 2-4 horas\n")
        f.write("Fase 3 (Migración datos): 4-8 horas\n")
        f.write("Fase 4 (Personalizaciones): 2-4 horas\n")
        f.write("Fase 5 (Verificación): 4-8 horas\n")
        f.write("Fase 6 (Puesta en producción): 2-4 horas\n")
        f.write("\nTiempo total estimado: 18-36 horas\n")
        f.write("Tiempo recomendado: 3-5 días (incluyendo pruebas y ajustes)\n\n")
        
        # Recomendaciones
        f.write("RECOMENDACIONES\n")
        f.write("="*80 + "\n")
        f.write("1. Realizar migración en horario de bajo tráfico\n")
        f.write("2. Tener servidor de respaldo disponible\n")
        f.write("3. Realizar pruebas exhaustivas antes de go-live\n")
        f.write("4. Tener plan de rollback preparado\n")
        f.write("5. Comunicar cambios a usuarios con anticipación\n")
        f.write("6. Capacitar usuarios en nuevas funcionalidades\n")
        f.write("7. Monitorear sistema durante primera semana\n")
        f.write("8. Documentar todos los cambios y configuraciones\n\n")
        
        f.write("="*80 + "\n")
        f.write("FIN DEL PLAN DE MIGRACIÓN\n")
        f.write("="*80 + "\n")
    
    print(f"\n✓ Plan detallado generado: {report_path}")
    return report_path


if __name__ == "__main__":
    generate_detailed_plan()
    print("\n✓ Análisis y plan de migración completados")

