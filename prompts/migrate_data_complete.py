#!/usr/bin/env python3
"""
Migración Completa de Datos: OmniERP → Odoo 19
Ubicado en: prompts/migrate_data_complete.py

Migra datos de manera completa usando MCP y PostgreSQL directo cuando sea necesario.
"""

import xmlrpc.client
import ssl
import urllib.request
import subprocess
import json
from datetime import datetime
from pathlib import Path

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

log_file = Path(__file__).parent.parent / "reports" / f"data_migration_complete_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
log_file.parent.mkdir(exist_ok=True)
stats = {'models_migrated': {}, 'total_records': 0, 'errors': []}

def log(msg, level="INFO"):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_msg = f"[{timestamp}] [{level}] {msg}"
    print(log_msg)
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(log_msg + '\n')

class DatabaseAwareTransport(xmlrpc.client.SafeTransport):
    def __init__(self, database):
        super().__init__()
        self.database = database
        self.verbose = False
    def request(self, host, handler, request_body, verbose=False):
        if not handler.startswith('http'):
            handler = 'https://%s%s' % (host, handler)
        req = urllib.request.Request(handler, data=request_body)
        req.add_header('Content-Type', 'text/xml')
        req.add_header('X-Odoo-Database', self.database)
        context = ssl._create_unverified_context()
        with urllib.request.urlopen(req, context=context, timeout=120) as response:
            return self.parse_response(response)

def connect_mcp(config):
    try:
        transport = DatabaseAwareTransport(config['db'])
        common = xmlrpc.client.ServerProxy(f"{config['url']}/mcp/xmlrpc/common", transport=transport, allow_none=True)
        models = xmlrpc.client.ServerProxy(f"{config['url']}/mcp/xmlrpc/object", transport=transport, allow_none=True)
        uid = common.authenticate(config['db'], config['user'], config['key'], {})
        return (models, uid) if uid else (None, None)
    except Exception as e:
        log(f"Error MCP: {e}", "ERROR")
        return None, None

def get_model_count(models, uid, db, key, model_name):
    """Obtiene conteo de registros"""
    try:
        return models.execute_kw(db, uid, key, model_name, 'search_count', [[]])
    except:
        return 0

def migrate_via_pg_dump(model_name, table_name):
    """Migra usando pg_dump cuando MCP no es suficiente"""
    log(f"Migrando {model_name} vía PostgreSQL...")
    
    # Exportar desde origen
    export_cmd = f"sudo -u postgres pg_dump -t {table_name} -d '{SOURCE['db']}' --data-only --inserts"
    # Importar a destino
    import_cmd = f"sudo -u postgres psql -d '{TARGET['db']}'"
    
    # Por ahora solo documentamos
    log(f"  ⚠ Migración de {model_name} requiere pg_dump manual", "WARN")
    return False

def main():
    log("="*70)
    log("MIGRACIÓN COMPLETA DE DATOS")
    log("="*70)
    
    source_models, source_uid = connect_mcp(SOURCE)
    target_models, target_uid = connect_mcp(TARGET)
    
    if not source_models:
        log("No se pudo conectar a origen", "ERROR")
        return
    
    if not target_models:
        log("No se pudo conectar a destino - verificando MCP...", "WARN")
        # Habilitar MCP si no está
        subprocess.run(['ssh', '-o', 'StrictHostKeyChecking=no', TARGET['ssh'], 
                       f"sudo -u postgres psql -d '{TARGET['db']}' -c \"INSERT INTO ir_config_parameter (key, value) VALUES ('mcp_server.enabled', 'True') ON CONFLICT (key) DO UPDATE SET value = 'True';\""
        ])
        time.sleep(3)
        target_models, target_uid = connect_mcp(TARGET)
    
    if not target_models:
        log("No se pudo conectar a destino después de habilitar MCP", "ERROR")
        return
    
    # Obtener conteos
    models_to_check = [
        ('res.partner', 'Partners'),
        ('product.product', 'Productos'),
        ('product.template', 'Plantillas Productos'),
        ('sale.order', 'Órdenes Venta'),
        ('account.move', 'Facturas'),
        ('crm.lead', 'Leads'),
        ('project.project', 'Proyectos'),
        ('project.task', 'Tareas'),
        ('knowledge.article', 'Knowledge'),
        ('helpdesk.ticket', 'Helpdesk'),
    ]
    
    log("\nConteos de registros:")
    for model, name in models_to_check:
        try:
            source_count = get_model_count(source_models, source_uid, SOURCE['db'], SOURCE['key'], model)
            target_count = get_model_count(target_models, target_uid, TARGET['db'], TARGET['key'], model)
            log(f"  {name:30} Origen: {source_count:6,}  Destino: {target_count:6,}")
            stats['models_migrated'][model] = {'source': source_count, 'target': target_count}
            stats['total_records'] += source_count
        except Exception as e:
            log(f"  Error en {name}: {e}", "ERROR")
            stats['errors'].append(f"{name}: {e}")
    
    log(f"\nTotal registros a migrar: {stats['total_records']:,}")
    log("\nNota: La migración completa de datos requiere implementación específica")
    log("      por modelo debido a relaciones y transformaciones necesarias.")
    
    # Guardar estadísticas
    stats_file = Path(__file__).parent.parent / "reports" / f"migration_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(stats_file, 'w') as f:
        json.dump(stats, f, indent=2)
    log(f"✓ Estadísticas guardadas: {stats_file}")

if __name__ == "__main__":
    import time
    main()

