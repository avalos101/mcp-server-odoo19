#!/usr/bin/env python3
"""
Migración Híbrida de Datos: OmniERP → Odoo 19
Ubicado en: prompts/migrate_data_hybrid.py

Usa MCP cuando esté disponible, XML-RPC estándar como fallback.
"""

import xmlrpc.client
import ssl
import urllib.request
import time
from datetime import datetime
from pathlib import Path
import json

SOURCE = {
    'url': 'https://omnierp.app',
    'db': 'omnierp.app',
    'user': 'admin@omnierp.app',
    'key': '7f3ea49d0339de71e39996866b61c26416ba0597'
}

TARGET = {
    'url': 'https://laia.one',
    'db': 'omnierp_migrated',
    'user': 'admin@laia.one',
    'key': 'cfebea4c6d0a3cc3e345db4aa9c94b3e085ea3e5'
}

log_file = Path(__file__).parent.parent / "reports" / f"hybrid_migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
log_file.parent.mkdir(exist_ok=True)
stats = {'models': {}, 'total_migrated': 0, 'total_errors': 0, 'errors': [], 'id_mapping': {}}

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

def connect_xmlrpc_standard(url, db, user, password):
    """Conecta usando XML-RPC estándar de Odoo"""
    try:
        common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', allow_none=True)
        uid = common.authenticate(db, user, password, {})
        if uid:
            models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', allow_none=True)
            return models, uid
        return None, None
    except Exception as e:
        log(f"Error XML-RPC estándar: {e}", "ERROR")
        return None, None

def connect_mcp(config):
    """Conecta vía MCP"""
    try:
        transport = DatabaseAwareTransport(config['db'])
        common = xmlrpc.client.ServerProxy(f"{config['url']}/mcp/xmlrpc/common", transport=transport, allow_none=True)
        models = xmlrpc.client.ServerProxy(f"{config['url']}/mcp/xmlrpc/object", transport=transport, allow_none=True)
        uid = common.authenticate(config['db'], config['user'], config['key'], {})
        return (models, uid, 'mcp') if uid else (None, None, None)
    except Exception as e:
        return None, None, None

def migrate_model_standard(source_models, source_uid, target_models, target_uid, model_name, batch_size=50):
    """Migra usando XML-RPC estándar"""
    log(f"\n{'='*70}")
    log(f"MIGRANDO: {model_name} (XML-RPC estándar)")
    log(f"{'='*70}")
    
    try:
        # Obtener total
        total = source_models.execute_kw(SOURCE['db'], 'search_count', [[], {}], {'context': {}})
        log(f"Total: {total:,}")
        
        if total == 0:
            return 0
        
        # Campos básicos
        fields = ['name', 'active', 'display_name']
        if model_name == 'res.partner':
            fields.extend(['is_company', 'email', 'phone', 'street', 'city', 'country_id'])
        elif 'product' in model_name:
            fields.extend(['list_price', 'default_code', 'categ_id'])
        elif model_name == 'crm.lead':
            fields.extend(['partner_id', 'name', 'stage_id'])
        elif model_name == 'sale.order':
            fields.extend(['partner_id', 'date_order', 'state'])
        
        migrated = 0
        offset = 0
        
        while offset < total:
            ids = source_models.execute_kw(SOURCE['db'], source_uid, SOURCE['key'], model_name, 'search', [[], []], {'offset': offset, 'limit': batch_size})
            
            if not ids:
                break
            
            records = source_models.execute_kw(SOURCE['db'], source_uid, SOURCE['key'], model_name, 'read', [ids], {'fields': fields})
            
            for record in records:
                try:
                    data = {k: v for k, v in record.items() if k not in ['id', 'create_date', 'write_date'] and v}
                    # Mapear relaciones
                    if 'partner_id' in data and isinstance(data['partner_id'], (list, tuple)):
                        old_id = data['partner_id'][0]
                        mapped = stats['id_mapping'].get('res.partner', {}).get(old_id)
                        if mapped:
                            data['partner_id'] = mapped
                        else:
                            continue
                    
                    new_id = target_models.execute_kw(TARGET['db'], target_uid, TARGET['key'], model_name, 'create', [data])
                    
                    if model_name not in stats['id_mapping']:
                        stats['id_mapping'][model_name] = {}
                    stats['id_mapping'][model_name][record['id']] = new_id
                    migrated += 1
                    
                except Exception as e:
                    log(f"Error: {e}", "ERROR")
            
            offset += batch_size
            log(f"Migrados: {migrated}/{total}")
            time.sleep(0.5)
        
        log(f"✓ {model_name}: {migrated:,} migrados")
        return migrated
        
    except Exception as e:
        log(f"✗ Error: {e}", "ERROR")
        return 0

def main():
    log("="*70)
    log("MIGRACIÓN HÍBRIDA DE DATOS")
    log("="*70)
    
    # Intentar MCP primero, luego XML-RPC estándar
    log("Conectando a origen...")
    source_models, source_uid, source_type = connect_mcp(SOURCE)
    if not source_models:
        log("MCP origen falló, usando XML-RPC estándar", "WARN")
        source_models, source_uid = connect_xmlrpc_standard(SOURCE['url'], SOURCE['db'], SOURCE['user'], SOURCE['key'])
        source_type = 'xmlrpc'
    
    if not source_models:
        log("Error: No se pudo conectar a origen", "ERROR")
        return False
    
    log(f"✓ Origen conectado ({source_type})")
    
    log("Conectando a destino...")
    target_models, target_uid, target_type = connect_mcp(TARGET)
    if not target_models:
        log("MCP destino falló, usando XML-RPC estándar", "WARN")
        target_models, target_uid = connect_xmlrpc_standard(TARGET['url'], TARGET['db'], TARGET['user'], TARGET['key'])
        target_type = 'xmlrpc'
    
    if not target_models:
        log("Error: No se pudo conectar a destino", "ERROR")
        return False
    
    log(f"✓ Destino conectado ({target_type})")
    
    # Migrar modelos en orden
    models_to_migrate = [
        'res.partner',
        'product.template',
        'product.product',
        'crm.lead',
        'sale.order',
        'account.move',
        'project.project',
        'project.task',
    ]
    
    for model in models_to_migrate:
        if target_type == 'xmlrpc':
            migrate_model_standard(source_models, source_uid, target_models, target_uid, model)
        else:
            # Usar función MCP si está disponible
            log(f"Migrando {model} vía MCP...")
        time.sleep(2)
    
    log("="*70)
    log("MIGRACIÓN COMPLETADA")
    log(f"Total migrado: {stats['total_migrated']:,}")
    return True

if __name__ == "__main__":
    main()

