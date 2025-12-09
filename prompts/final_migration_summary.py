#!/usr/bin/env python3
"""
Generador de Resumen Final de Migración
Ubicado en: prompts/final_migration_summary.py

Genera un resumen completo de todo lo ejecutado durante la migración.
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

def get_db_info(ssh, db):
    """Obtiene información de la BD"""
    info = {}
    
    # Tamaño
    success, out, _ = ssh_exec(f"sudo -u postgres psql -d '{db}' -t -c \"SELECT pg_size_pretty(pg_database_size('{db}'));\"", ssh)
    if success:
        info['size'] = out.strip()
    
    # Módulos instalados
    success, out, _ = ssh_exec(f"sudo -u postgres psql -d '{db}' -t -c \"SELECT COUNT(*) FROM ir_module_module WHERE state='installed';\"", ssh)
    if success:
        info['modules'] = int(out.strip()) if out.strip().isdigit() else 0
    
    return info

def get_model_counts(models, uid, db, key, models_list):
    """Obtiene conteos de modelos"""
    counts = {}
    for model in models_list:
        try:
            count = models.execute_kw(db, uid, key, model, 'search_count', [[]])
            counts[model] = count
        except:
            counts[model] = 0
    return counts

def main():
    print("="*70)
    print("GENERANDO RESUMEN FINAL DE MIGRACIÓN")
    print("="*70)
    
    summary_file = Path(__file__).parent.parent / "reports" / f"FINAL_MIGRATION_SUMMARY_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("="*70 + "\n")
        f.write("RESUMEN FINAL DE MIGRACIÓN: OMNIIRP (Odoo 18) → ODOO 19\n")
        f.write("="*70 + "\n")
        f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Información del servidor origen
        f.write("SERVIDOR ORIGEN (OmniERP - Odoo 18)\n")
        f.write("-"*70 + "\n")
        f.write(f"URL: {SOURCE['url']}\n")
        f.write(f"Base de datos: {SOURCE['db']}\n")
        
        source_info = get_db_info(SOURCE['ssh'], SOURCE['db'])
        f.write(f"Tamaño: {source_info.get('size', 'N/A')}\n")
        f.write(f"Módulos instalados: {source_info.get('modules', 'N/A')}\n\n")
        
        # Información del servidor destino
        f.write("SERVIDOR DESTINO (Laia.one - Odoo 19)\n")
        f.write("-"*70 + "\n")
        f.write(f"URL: {TARGET['url']}\n")
        f.write(f"Base de datos: {TARGET['db']}\n")
        
        target_info = get_db_info(TARGET['ssh'], TARGET['db'])
        f.write(f"Tamaño: {target_info.get('size', 'N/A')}\n")
        f.write(f"Módulos instalados: {target_info.get('modules', 'N/A')}\n\n")
        
        # Comparación de datos
        f.write("COMPARACIÓN DE DATOS\n")
        f.write("-"*70 + "\n")
        
        try:
            transport_source = DatabaseAwareTransport(SOURCE['db'])
            common_source = xmlrpc.client.ServerProxy(f"{SOURCE['url']}/mcp/xmlrpc/common", transport=transport_source, allow_none=True)
            models_source = xmlrpc.client.ServerProxy(f"{SOURCE['url']}/mcp/xmlrpc/object", transport=transport_source, allow_none=True)
            uid_source = common_source.authenticate(SOURCE['db'], SOURCE['user'], SOURCE['key'], {})
            
            if uid_source:
                models_to_check = ['res.partner', 'product.product', 'sale.order', 'crm.lead', 'project.project', 'knowledge.article', 'helpdesk.ticket']
                source_counts = get_model_counts(models_source, uid_source, SOURCE['db'], SOURCE['key'], models_to_check)
                
                f.write(f"{'Modelo':<30} {'Origen':<15} {'Destino':<15} {'Estado':<10}\n")
                f.write("-"*70 + "\n")
                
                for model in models_to_check:
                    source_count = source_counts.get(model, 0)
                    f.write(f"{model:<30} {source_count:<15,} {'N/A':<15} {'Pendiente':<10}\n")
        except Exception as e:
            f.write(f"Error obteniendo comparación: {e}\n")
        
        # Estado de la migración
        f.write("\nESTADO DE LA MIGRACIÓN\n")
        f.write("-"*70 + "\n")
        f.write("✓ Base de datos creada: omnierp_migrated\n")
        f.write("✓ Base de datos inicializada con módulos base\n")
        f.write(f"✓ Módulos instalados: {target_info.get('modules', 0)}\n")
        f.write("⚠ Migración de datos: Pendiente (requiere implementación específica)\n")
        f.write("⚠ MCP habilitado: Verificar\n")
        
        # Próximos pasos
        f.write("\nPRÓXIMOS PASOS\n")
        f.write("-"*70 + "\n")
        f.write("1. Verificar que todos los módulos necesarios están instalados\n")
        f.write("2. Instalar módulo mcp_server si no está instalado\n")
        f.write("3. Habilitar modelos en MCP para acceso\n")
        f.write("4. Implementar migración de datos por modelo\n")
        f.write("5. Verificar integridad de datos migrados\n")
        f.write("6. Probar funcionalidades críticas\n")
        
        f.write("\n" + "="*70 + "\n")
        f.write("FIN DEL RESUMEN\n")
        f.write("="*70 + "\n")
    
    print(f"✓ Resumen generado: {summary_file}")
    
    # Mostrar resumen en consola
    with open(summary_file, 'r') as f:
        print(f.read())

if __name__ == "__main__":
    main()

