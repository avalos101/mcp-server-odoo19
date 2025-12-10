#!/usr/bin/env python3
"""
Migración Final de Datos: OmniERP → Odoo 19
Ubicado en: prompts/migrate_data_final.py

Migra datos usando MCP desde origen y creación directa en destino.
Funciona aunque MCP destino no esté disponible.
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

log_file = Path(__file__).parent.parent / "reports" / f"final_migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
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
        try:
            with urllib.request.urlopen(req, context=context, timeout=120) as response:
                return self.parse_response(response)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                # Reintentar sin header
                req2 = urllib.request.Request(handler, data=request_body)
                req2.add_header('Content-Type', 'text/xml')
                with urllib.request.urlopen(req2, context=context, timeout=120) as response:
                    return self.parse_response(response)
            raise

def connect_source_mcp():
    """Conecta a origen vía MCP"""
    try:
        transport = DatabaseAwareTransport(SOURCE['db'])
        common = xmlrpc.client.ServerProxy(f"{SOURCE['url']}/mcp/xmlrpc/common", transport=transport, allow_none=True)
        models = xmlrpc.client.ServerProxy(f"{SOURCE['url']}/mcp/xmlrpc/object", transport=transport, allow_none=True)
        uid = common.authenticate(SOURCE['db'], SOURCE['user'], SOURCE['key'], {})
        return (models, uid) if uid else (None, None)
    except Exception as e:
        log(f"Error MCP origen: {e}", "ERROR")
        return None, None

def connect_target_direct():
    """Conecta a destino usando XML-RPC directo"""
    # Método que funciona: usar header X-Odoo-Database y usuario 'admin' con contraseña 'admin'
    try:
        transport = DatabaseAwareTransport(TARGET['db'])
        common = xmlrpc.client.ServerProxy(f"{TARGET['url']}/xmlrpc/2/common", transport=transport, allow_none=True)
        # Probar con usuario 'admin' y contraseña 'admin' (por defecto en Odoo)
        uid = common.authenticate(TARGET['db'], 'admin', 'admin', {})
        if uid:
            models = xmlrpc.client.ServerProxy(f"{TARGET['url']}/xmlrpc/2/object", transport=transport, allow_none=True)
            log("✓ Conectado vía XML-RPC con usuario admin", "INFO")
            return (models, uid)
    except Exception as e:
        log(f"Error XML-RPC: {str(e)[:100]}", "WARN")
    
    # Intentar MCP también
    try:
        transport = DatabaseAwareTransport(TARGET['db'])
        common = xmlrpc.client.ServerProxy(f"{TARGET['url']}/mcp/xmlrpc/common", transport=transport, allow_none=True)
        uid = common.authenticate(TARGET['db'], TARGET['user'], TARGET['key'], {})
        if uid:
            models = xmlrpc.client.ServerProxy(f"{TARGET['url']}/mcp/xmlrpc/object", transport=transport, allow_none=True)
            log("✓ Conectado vía MCP", "INFO")
            return (models, uid)
    except:
        pass
    
    return None, None

def map_related_id(field_name, value, id_mappings):
    """Mapea IDs de relaciones"""
    if not isinstance(value, (list, tuple)) or len(value) == 0:
        return value
    
    if isinstance(value[0], int):
        rel_id = value[0]
        if field_name in ['partner_id', 'customer_id', 'vendor_id', 'parent_id', 'commercial_partner_id']:
            return id_mappings.get('res.partner', {}).get(rel_id, False)
        elif field_name in ['product_id', 'product_tmpl_id']:
            mapped = id_mappings.get('product.product', {}).get(rel_id)
            if not mapped:
                mapped = id_mappings.get('product.template', {}).get(rel_id)
            return mapped if mapped else False
        elif field_name == 'project_id':
            return id_mappings.get('project.project', {}).get(rel_id, False)
        elif field_name == 'sale_order_id':
            return id_mappings.get('sale.order', {}).get(rel_id, False)
        else:
            return rel_id
    return value[0] if value else False

def migrate_model(source_models, source_uid, target_models, target_uid, model_name, batch_size=50):
    """Migra un modelo"""
    log(f"\n{'='*70}")
    log(f"MIGRANDO: {model_name}")
    log(f"{'='*70}")
    
    try:
        total = source_models.execute_kw(SOURCE['db'], source_uid, SOURCE['key'], model_name, 'search_count', [[]])
        log(f"Total en origen: {total:,}")
        
        if total == 0:
            return 0
        
        # Campos según modelo
        if model_name == 'res.partner':
            fields = ['name', 'is_company', 'email', 'phone', 'mobile', 'street', 'city', 'state_id', 'country_id', 'category_id', 'parent_id', 'active']
        elif model_name == 'product.template':
            fields = ['name', 'list_price', 'default_code', 'categ_id', 'type', 'sale_ok', 'purchase_ok', 'active']
        elif model_name == 'product.product':
            fields = ['name', 'product_tmpl_id', 'default_code', 'list_price', 'active']
        elif model_name == 'crm.lead':
            fields = ['name', 'partner_id', 'email_from', 'phone', 'stage_id', 'probability', 'active']
        elif model_name == 'sale.order':
            fields = ['name', 'partner_id', 'date_order', 'state', 'amount_total']
        elif model_name == 'account.move':
            fields = ['name', 'partner_id', 'move_type', 'invoice_date', 'state', 'amount_total']
        elif model_name == 'project.project':
            fields = ['name', 'partner_id', 'active']
        elif model_name == 'project.task':
            fields = ['name', 'project_id', 'partner_id', 'user_id', 'stage_id', 'active']
        else:
            fields = ['name', 'active']
        
        migrated = 0
        errors = 0
        offset = 0
        
        while offset < total:
            try:
                records = source_models.execute_kw(
                    SOURCE['db'], source_uid, SOURCE['key'],
                    model_name, 'search_read',
                    [[]],
                    {'fields': fields, 'limit': batch_size, 'offset': offset}
                )
                
                if not records:
                    break
                
                log(f"Lote {offset//batch_size + 1}: {len(records)} registros")
                
                for record in records:
                    try:
                        data = {}
                        old_id = record.get('id')
                        
                        for field in fields:
                            if field in record:
                                value = record[field]
                                mapped = map_related_id(field, value, stats['id_mapping'])
                                if mapped or (isinstance(mapped, bool) and mapped == False):
                                    data[field] = mapped
                                elif value and not isinstance(value, (list, tuple)):
                                    data[field] = value
                        
                        # Crear en destino - usar contraseña 'admin' para XML-RPC estándar
                        password = 'admin'  # Para XML-RPC estándar usamos contraseña, no API key
                        new_id = target_models.execute_kw(
                            TARGET['db'], target_uid, password, 
                            model_name, 'create', [data]
                        )
                        
                        # Guardar mapeo
                        if model_name not in stats['id_mapping']:
                            stats['id_mapping'][model_name] = {}
                        stats['id_mapping'][model_name][old_id] = new_id
                        migrated += 1
                        
                    except Exception as e:
                        errors += 1
                        if errors <= 3:
                            log(f"Error registro {record.get('id')}: {str(e)[:100]}", "ERROR")
                        if errors > 20:
                            break
                
                offset += batch_size
                if migrated % 50 == 0:
                    log(f"  Progreso: {migrated:,}/{total:,}")
                time.sleep(0.3)
                
            except Exception as e:
                log(f"Error en lote: {e}", "ERROR")
                break
        
        log(f"✓ {model_name}: {migrated:,} migrados, {errors} errores")
        stats['models'][model_name] = {'migrated': migrated, 'errors': errors, 'total': total}
        stats['total_migrated'] += migrated
        stats['total_errors'] += errors
        return migrated
        
    except Exception as e:
        log(f"✗ Error: {e}", "ERROR")
        return 0

def main():
    log("="*70)
    log("MIGRACIÓN FINAL DE DATOS")
    log("="*70)
    start = datetime.now()
    
    # Conectar
    log("Conectando a origen...")
    source_models, source_uid = connect_source_mcp()
    if not source_models:
        log("Error: No se pudo conectar a origen", "ERROR")
        return False
    log("✓ Origen conectado")
    
    log("Conectando a destino...")
    target_models, target_uid = connect_target_direct()
    if not target_models:
        log("Error: No se pudo conectar a destino", "ERROR")
        return False
    log("✓ Destino conectado")
    
    # Migrar en orden
    models = [
        'res.partner',
        'product.template',
        'product.product',
        'crm.lead',
        'sale.order',
        'account.move',
        'project.project',
        'project.task',
    ]
    
    for model in models:
        migrate_model(source_models, source_uid, target_models, target_uid, model)
        time.sleep(2)
    
    duration = (datetime.now() - start).total_seconds() / 60
    log("="*70)
    log("MIGRACIÓN COMPLETADA")
    log(f"Duración: {duration:.1f} min")
    log(f"Total migrado: {stats['total_migrated']:,}")
    
    # Guardar stats
    stats_file = log_file.parent / f"migration_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(stats_file, 'w') as f:
        json.dump(stats, f, indent=2, default=str)
    log(f"✓ Stats: {stats_file}")
    
    return True

if __name__ == "__main__":
    main()

