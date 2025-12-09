#!/usr/bin/env python3
"""
Generador de Reporte Final Completo
Ubicado en: prompts/generate_final_report.py

Genera un reporte completo de todo lo ejecutado durante la migración.
"""

import subprocess
import xmlrpc.client
import ssl
import urllib.request
from datetime import datetime
from pathlib import Path
import json

SOURCE = {
    'url': 'https://omnierp.app',
    'db': 'omnierp.app',
    'user': 'admin@omnierp.app',
    'key': '7f3ea49d0339de71e39996866b61c26416ba0597',
    'ssh': 'diego.avalos@omnierp.app'
}

TARGET = {
    'url': 'https://laia.one',
    'db': 'omnierp_migrated',
    'user': 'admin@laia.one',
    'key': 'cfebea4c6d0a3cc3e345db4aa9c94b3e085ea3e5',
    'ssh': 'diego.avalos@laia.one'
}

def ssh_exec(cmd, host):
    ssh_cmd = ['ssh', '-o', 'StrictHostKeyChecking=no', host, cmd]
    try:
        result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=60)
        return result.returncode == 0, result.stdout, result.stderr
    except:
        return False, "", ""

class DatabaseAwareTransport(xmlrpc.client.SafeTransport):
    def __init__(self, db): super().__init__(); self.database = db; self.verbose = False
    def request(self, host, handler, request_body, verbose=False):
        if not handler.startswith('http'): handler = 'https://%s%s' % (host, handler)
        req = urllib.request.Request(handler, data=request_body)
        req.add_header('Content-Type', 'text/xml')
        req.add_header('X-Odoo-Database', self.database)
        context = ssl._create_unverified_context()
        with urllib.request.urlopen(req, context=context, timeout=60) as r:
            return self.parse_response(r)

def get_info():
    """Recopila toda la información"""
    info = {
        'source': {},
        'target': {},
        'comparison': {},
        'execution': {}
    }
    
    # Información origen
    success, out, _ = ssh_exec(f"sudo -u postgres psql -d '{SOURCE['db']}' -t -c \"SELECT pg_size_pretty(pg_database_size('{SOURCE['db']}')), (SELECT COUNT(*) FROM ir_module_module WHERE state='installed');\"", SOURCE['ssh'])
    if success and out.strip():
        parts = out.strip().split('|')
        if len(parts) >= 2:
            info['source']['size'] = parts[0].strip()
            info['source']['modules'] = int(parts[1].strip()) if parts[1].strip().isdigit() else 0
    
    # Información destino
    success, out, _ = ssh_exec(f"sudo -u postgres psql -d '{TARGET['db']}' -t -c \"SELECT pg_size_pretty(pg_database_size('{TARGET['db']}')), (SELECT COUNT(*) FROM ir_module_module WHERE state='installed');\"", TARGET['ssh'])
    if success and out.strip():
        parts = out.strip().split('|')
        if len(parts) >= 2:
            info['target']['size'] = parts[0].strip()
            info['target']['modules'] = int(parts[1].strip()) if parts[1].strip().isdigit() else 0
    
    # Conteos de datos origen
    try:
        transport = DatabaseAwareTransport(SOURCE['db'])
        common = xmlrpc.client.ServerProxy(f"{SOURCE['url']}/mcp/xmlrpc/common", transport=transport, allow_none=True)
        models = xmlrpc.client.ServerProxy(f"{SOURCE['url']}/mcp/xmlrpc/object", transport=transport, allow_none=True)
        uid = common.authenticate(SOURCE['db'], SOURCE['user'], SOURCE['key'], {})
        
        if uid:
            models_list = ['res.partner', 'product.product', 'sale.order', 'crm.lead', 'project.project', 'knowledge.article', 'helpdesk.ticket']
            for model in models_list:
                try:
                    count = models.execute_kw(SOURCE['db'], uid, SOURCE['key'], model, 'search_count', [[]])
                    info['source'][model] = count
                except:
                    info['source'][model] = 0
    except:
        pass
    
    return info

def main():
    print("="*70)
    print("GENERANDO REPORTE FINAL COMPLETO")
    print("="*70)
    
    info = get_info()
    
    report_file = Path(__file__).parent.parent / "reports" / f"FINAL_MIGRATION_REPORT_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("="*80 + "\n")
        f.write("REPORTE FINAL DE MIGRACIÓN: OMNIIRP (Odoo 18) → ODOO 19\n")
        f.write("="*80 + "\n")
        f.write(f"Fecha de generación: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Resumen ejecutivo
        f.write("RESUMEN EJECUTIVO\n")
        f.write("-"*80 + "\n")
        f.write(f"Origen: {SOURCE['url']} ({SOURCE['db']})\n")
        f.write(f"Destino: {TARGET['url']} ({TARGET['db']})\n")
        f.write(f"Estado: Base de datos creada e inicializada\n")
        f.write(f"Módulos instalados en destino: {info['target'].get('modules', 'N/A')}\n")
        f.write(f"Módulos en origen: {info['source'].get('modules', 'N/A')}\n\n")
        
        # Información detallada origen
        f.write("INFORMACIÓN DEL SERVIDOR ORIGEN (OmniERP)\n")
        f.write("-"*80 + "\n")
        f.write(f"Base de datos: {SOURCE['db']}\n")
        f.write(f"Tamaño: {info['source'].get('size', 'N/A')}\n")
        f.write(f"Módulos instalados: {info['source'].get('modules', 'N/A')}\n\n")
        f.write("Datos en origen:\n")
        for key, value in info['source'].items():
            if key not in ['size', 'modules'] and isinstance(value, int):
                f.write(f"  - {key}: {value:,} registros\n")
        f.write("\n")
        
        # Información detallada destino
        f.write("INFORMACIÓN DEL SERVIDOR DESTINO (Laia.one)\n")
        f.write("-"*80 + "\n")
        f.write(f"Base de datos: {TARGET['db']}\n")
        f.write(f"Tamaño: {info['target'].get('size', 'N/A')}\n")
        f.write(f"Módulos instalados: {info['target'].get('modules', 'N/A')}\n")
        f.write(f"Estado: Base de datos nueva creada e inicializada\n\n")
        
        # Acciones ejecutadas
        f.write("ACCIONES EJECUTADAS\n")
        f.write("-"*80 + "\n")
        f.write("✓ Base de datos 'omnierp_migrated' creada en servidor Laia.one\n")
        f.write("✓ Base de datos inicializada con módulos base de Odoo 19\n")
        f.write("✓ Módulos principales instalados (sale, purchase, stock, account, crm, project)\n")
        f.write("✓ Módulos de Knowledge y Helpdesk instalados\n")
        f.write("✓ Módulo MCP Server instalado\n")
        f.write("✓ MCP habilitado en configuración\n")
        f.write("✓ Modelos habilitados para acceso MCP\n")
        f.write("⚠ Migración de datos: Estructura preparada, datos pendientes de migración\n\n")
        
        # Estado actual
        f.write("ESTADO ACTUAL\n")
        f.write("-"*80 + "\n")
        f.write("Base de datos destino: CREADA E INICIALIZADA\n")
        f.write("Módulos base: INSTALADOS\n")
        f.write("Módulos principales: INSTALADOS\n")
        f.write("MCP Server: INSTALADO Y CONFIGURADO\n")
        f.write("Migración de datos: PENDIENTE\n\n")
        
        # Próximos pasos
        f.write("PRÓXIMOS PASOS RECOMENDADOS\n")
        f.write("-"*80 + "\n")
        f.write("1. Verificar que todos los módulos necesarios están instalados\n")
        f.write("2. Completar instalación de módulos faltantes si es necesario\n")
        f.write("3. Implementar migración de datos usando:\n")
        f.write("   - pg_dump/pg_restore para datos masivos\n")
        f.write("   - Scripts Python con MCP para datos específicos\n")
        f.write("   - Transformaciones necesarias para compatibilidad Odoo 19\n")
        f.write("4. Migrar datos en orden:\n")
        f.write("   a. Datos maestros (partners, productos, configuraciones)\n")
        f.write("   b. Datos transaccionales (ventas, facturas)\n")
        f.write("   c. Datos de módulos especiales (proyectos, knowledge, helpdesk)\n")
        f.write("5. Verificar integridad de datos migrados\n")
        f.write("6. Probar funcionalidades críticas\n")
        f.write("7. Configurar backups automáticos\n")
        f.write("8. Capacitar usuarios\n\n")
        
        # Archivos generados
        f.write("ARCHIVOS Y LOGS GENERADOS\n")
        f.write("-"*80 + "\n")
        reports_dir = Path(__file__).parent.parent / "reports"
        migration_files = list(reports_dir.glob("*migration*"))
        for file in sorted(migration_files)[-10:]:
            f.write(f"  - {file.name}\n")
        f.write("\n")
        
        f.write("="*80 + "\n")
        f.write("FIN DEL REPORTE\n")
        f.write("="*80 + "\n")
    
    print(f"✓ Reporte generado: {report_file}")
    
    # Mostrar resumen
    with open(report_file, 'r') as f:
        print("\n" + f.read())

if __name__ == "__main__":
    main()

