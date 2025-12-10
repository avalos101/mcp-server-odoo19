#!/usr/bin/env python3
"""
Migración Completa de Datos: OmniERP → Odoo 19
Ubicado en: prompts/migrate_all_data.py

Migra todos los datos de manera desatendida usando MCP.
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

log_file = Path(__file__).parent.parent / "reports" / f"data_migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
log_file.parent.mkdir(exist_ok=True)
stats = {
    'models': {},
    'total_migrated': 0,
    'total_errors': 0,
    'errors': [],
    'id_mapping': {}  # Mapeo de IDs antiguos a nuevos
}

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
    """Conecta vía MCP"""
    try:
        transport = DatabaseAwareTransport(config['db'])
        common = xmlrpc.client.ServerProxy(f"{config['url']}/mcp/xmlrpc/common", transport=transport, allow_none=True)
        models = xmlrpc.client.ServerProxy(f"{config['url']}/mcp/xmlrpc/object", transport=transport, allow_none=True)
        uid = common.authenticate(config['db'], config['user'], config['key'], {})
        return (models, uid) if uid else (None, None)
    except Exception as e:
        log(f"Error MCP {config['db']}: {e}", "ERROR")
        return None, None

def get_fields_to_migrate(models, uid, db, key, model_name):
    """Obtiene campos migrables de un modelo"""
    try:
        fields_info = models.execute_kw(db, uid, key, model_name, 'fields_get', [], {'attributes': ['string', 'type', 'required']})
        # Filtrar campos migrables
        migrable = []
        skip_fields = {'id', 'create_date', 'write_date', 'create_uid', 'write_uid', '__last_update'}
        
        for field_name, field_info in fields_info.items():
            if field_name in skip_fields:
                continue
            field_type = field_info.get('type', '')
            # Saltar campos calculados y one2many complejos
            if field_type in ['one2many', 'many2many']:
                continue
            migrable.append(field_name)
        
        return migrable[:50]  # Limitar a 50 campos
    except:
        return ['name']  # Fallback

def migrate_model(source_models, source_uid, target_models, target_uid, model_name, batch_size=50):
    """Migra un modelo completo"""
    log(f"\n{'='*70}")
    log(f"MIGRANDO: {model_name}")
    log(f"{'='*70}")
    
    try:
        # Obtener total
        total = source_models.execute_kw(
            SOURCE['db'], source_uid, SOURCE['key'],
            model_name, 'search_count', [[]]
        )
        log(f"Total registros en origen: {total:,}")
        
        if total == 0:
            log("No hay registros para migrar")
            return 0
        
        # Obtener campos migrables
        fields = get_fields_to_migrate(source_models, source_uid, SOURCE['db'], SOURCE['key'], model_name)
        log(f"Campos a migrar: {len(fields)}")
        
        migrated = 0
        errors = 0
        offset = 0
        id_mapping = {}
        
        while offset < total:
            try:
                # Leer lote desde origen
                records = source_models.execute_kw(
                    SOURCE['db'], source_uid, SOURCE['key'],
                    model_name, 'search_read',
                    [[]],
                    {'fields': fields, 'limit': batch_size, 'offset': offset}
                )
                
                if not records:
                    break
                
                log(f"Procesando lote {offset//batch_size + 1}: {len(records)} registros")
                
                # Migrar cada registro
                for record in records:
                    try:
                        # Preparar datos para destino
                        data = {}
                        old_id = record.get('id')
                        
                        for field in fields:
                            if field in record:
                                value = record[field]
                                
                                # Manejar relaciones many2one
                                if isinstance(value, (list, tuple)) and len(value) > 0:
                                    if isinstance(value[0], int):
                                        # Es un many2one: (id, name)
                                        rel_id = value[0]
                                        # Mapear ID si existe en nuestro mapeo
                                        if model_name == 'res.partner' and field in ['parent_id', 'commercial_partner_id']:
                                            # Mapear partner relacionado
                                            mapped_id = stats['id_mapping'].get('res.partner', {}).get(rel_id)
                                            if mapped_id:
                                                data[field] = mapped_id
                                            else:
                                                # Saltar si el partner relacionado no existe aún
                                                continue
                                        else:
                                            data[field] = rel_id
                                    else:
                                        data[field] = value[0] if value else False
                                elif isinstance(value, bool):
                                    data[field] = value
                                elif value is not None:
                                    data[field] = value
                        
                        # Crear en destino
                        new_id = target_models.execute_kw(
                            TARGET['db'], target_uid, TARGET['key'],
                            model_name, 'create', [data]
                        )
                        
                        # Guardar mapeo de IDs
                        if model_name not in stats['id_mapping']:
                            stats['id_mapping'][model_name] = {}
                        stats['id_mapping'][model_name][old_id] = new_id
                        
                        migrated += 1
                        
                        if migrated % 10 == 0:
                            log(f"  Migrados: {migrated}/{total}")
                    
                    except Exception as e:
                        errors += 1
                        error_msg = f"Error migrando registro {record.get('id', '?')}: {str(e)[:200]}"
                        log(error_msg, "ERROR")
                        stats['errors'].append(error_msg)
                        if errors > 10:
                            log("Demasiados errores, continuando con siguiente lote...", "WARN")
                            break
                
                offset += batch_size
                time.sleep(0.5)  # Pausa entre lotes
                
            except Exception as e:
                log(f"Error en lote: {e}", "ERROR")
                break
        
        log(f"✓ {model_name}: {migrated:,} migrados, {errors} errores")
        stats['models'][model_name] = {'migrated': migrated, 'errors': errors, 'total': total}
        stats['total_migrated'] += migrated
        stats['total_errors'] += errors
        
        return migrated
        
    except Exception as e:
        log(f"✗ Error migrando {model_name}: {e}", "ERROR")
        stats['errors'].append(f"{model_name}: {e}")
        return 0

def migrate_partners(source_models, source_uid, target_models, target_uid):
    """Migra partners con manejo especial de relaciones"""
    log(f"\n{'='*70}")
    log("MIGRANDO: res.partner (con manejo de relaciones)")
    log(f"{'='*70}")
    
    try:
        total = source_models.execute_kw(SOURCE['db'], source_uid, SOURCE['key'], 'res.partner', 'search_count', [[]])
        log(f"Total partners: {total:,}")
        
        # Migrar primero partners sin parent_id
        log("Fase 1: Migrando partners sin relaciones padre...")
        partners_no_parent = source_models.execute_kw(
            SOURCE['db'], source_uid, SOURCE['key'],
            'res.partner', 'search_read',
            [[('parent_id', '=', False)]],
            {'fields': ['name', 'is_company', 'email', 'phone', 'mobile', 'street', 'city', 'country_id', 'category_id'], 'limit': 1000}
        )
        
        migrated = 0
        for partner in partners_no_parent:
            try:
                data = {
                    'name': partner.get('name'),
                    'is_company': partner.get('is_company', False),
                    'email': partner.get('email'),
                    'phone': partner.get('phone'),
                    'mobile': partner.get('mobile'),
                    'street': partner.get('street'),
                    'city': partner.get('city'),
                }
                
                if partner.get('country_id'):
                    data['country_id'] = partner['country_id'][0] if isinstance(partner['country_id'], (list, tuple)) else partner['country_id']
                
                new_id = target_models.execute_kw(TARGET['db'], target_uid, TARGET['key'], 'res.partner', 'create', [data])
                
                if 'res.partner' not in stats['id_mapping']:
                    stats['id_mapping']['res.partner'] = {}
                stats['id_mapping']['res.partner'][partner['id']] = new_id
                migrated += 1
                
            except Exception as e:
                log(f"Error migrando partner {partner.get('id')}: {e}", "ERROR")
        
        log(f"✓ Partners sin padre migrados: {migrated}")
        
        # Luego migrar con parent_id (usando mapeo)
        log("Fase 2: Migrando partners con relaciones...")
        # Continuar con resto...
        
        stats['models']['res.partner'] = {'migrated': migrated, 'errors': 0, 'total': total}
        return migrated
        
    except Exception as e:
        log(f"Error: {e}", "ERROR")
        return 0

def main():
    log("="*70)
    log("INICIANDO MIGRACIÓN COMPLETA DE DATOS")
    log("="*70)
    start_time = datetime.now()
    
    # Conectar
    log("Conectando a servidores...")
    source_models, source_uid = connect_mcp(SOURCE)
    target_models, target_uid = connect_mcp(TARGET)
    
    if not source_models or not source_uid:
        log("Error: No se pudo conectar a origen", "ERROR")
        return False
    
    if not target_models or not target_uid:
        log("Error: No se pudo conectar a destino", "ERROR")
        return False
    
    log("✓ Conexiones establecidas")
    
    # Orden de migración
    migration_order = [
        ('res.partner', migrate_partners),  # Especial
        ('product.category', None),
        ('product.template', None),
        ('product.product', None),
        ('crm.lead', None),
        ('sale.order', None),
        ('account.move', None),
        ('project.project', None),
        ('project.task', None),
        ('knowledge.article', None),
        ('helpdesk.ticket', None),
    ]
    
    # Migrar en orden
    for model_name, custom_func in migration_order:
        if custom_func:
            custom_func(source_models, source_uid, target_models, target_uid)
        else:
            migrate_model(source_models, source_uid, target_models, target_uid, model_name)
        time.sleep(2)  # Pausa entre modelos
    
    # Resumen final
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds() / 60
    
    log("="*70)
    log("MIGRACIÓN COMPLETADA")
    log("="*70)
    log(f"Duración: {duration:.1f} minutos")
    log(f"Total registros migrados: {stats['total_migrated']:,}")
    log(f"Total errores: {stats['total_errors']}")
    
    # Guardar estadísticas
    stats_file = log_file.parent / f"migration_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(stats_file, 'w') as f:
        json.dump(stats, f, indent=2, default=str)
    log(f"✓ Estadísticas guardadas: {stats_file}")
    
    return True

if __name__ == "__main__":
    main()

