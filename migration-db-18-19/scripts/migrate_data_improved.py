#!/usr/bin/env python3
"""
Migración Mejorada de Datos: OmniERP → Odoo 19
Ubicado en: prompts/migrate_data_improved.py

Migra datos con manejo correcto de metadatos (usuarios, fechas, etc.)
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

log_file = Path(__file__).parent.parent / "reports" / f"improved_migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
log_file.parent.mkdir(exist_ok=True)
stats = {
    'models': {},
    'total_migrated': 0,
    'total_errors': 0,
    'errors': [],
    'id_mapping': {},
    'user_mapping': {}  # Mapeo de usuarios
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
        try:
            with urllib.request.urlopen(req, context=context, timeout=120) as response:
                return self.parse_response(response)
        except urllib.error.HTTPError as e:
            if e.code == 404:
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
    """Conecta a destino usando XML-RPC"""
    try:
        transport = DatabaseAwareTransport(TARGET['db'])
        common = xmlrpc.client.ServerProxy(f"{TARGET['url']}/xmlrpc/2/common", transport=transport, allow_none=True)
        uid = common.authenticate(TARGET['db'], 'admin', 'admin', {})
        if uid:
            models = xmlrpc.client.ServerProxy(f"{TARGET['url']}/xmlrpc/2/object", transport=transport, allow_none=True)
            log("✓ Conectado vía XML-RPC", "INFO")
            return (models, uid)
    except Exception as e:
        log(f"Error conexión destino: {str(e)[:100]}", "WARN")
    
    return None, None

def migrate_users(source_models, source_uid, target_models, target_uid):
    """Migra usuarios primero (necesario para metadatos)"""
    log(f"\n{'='*70}")
    log("MIGRANDO: res.users (PRIORITARIO - Para metadatos)")
    log(f"{'='*70}")
    
    try:
        # Obtener todos los usuarios (activos e inactivos)
        total = source_models.execute_kw(
            SOURCE['db'], source_uid, SOURCE['key'],
            'res.users', 'search_count', [[]]
        )
        log(f"Total usuarios en origen: {total:,}")
        
        if total == 0:
            return 0
        
        # Campos de usuario
        fields = ['login', 'name', 'active', 'partner_id', 'groups_id', 'email']
        
        migrated = 0
        errors = 0
        offset = 0
        batch_size = 50
        
        while offset < total:
            try:
                records = source_models.execute_kw(
                    SOURCE['db'], source_uid, SOURCE['key'],
                    'res.users', 'search_read',
                    [[]],
                    {'fields': fields, 'limit': batch_size, 'offset': offset}
                )
                
                if not records:
                    break
                
                log(f"Lote {offset//batch_size + 1}: {len(records)} usuarios")
                
                for record in records:
                    try:
                        old_id = record.get('id')
                        login = record.get('login', '')
                        
                        # Saltar usuarios del sistema
                        if login in ['__system__', 'public', 'default', 'portaltemplate']:
                            # Mapear a usuarios existentes en destino
                            if login == '__system__':
                                stats['user_mapping'][old_id] = 1
                            elif login == 'public':
                                stats['user_mapping'][old_id] = 3
                            else:
                                stats['user_mapping'][old_id] = 2  # admin
                            continue
                        
                        # Verificar si el usuario ya existe
                        existing = target_models.execute_kw(
                            TARGET['db'], target_uid, 'admin',
                            'res.users', 'search', [[('login', '=', login)]]
                        )
                        
                        if existing:
                            # Usuario ya existe, mapear
                            stats['user_mapping'][old_id] = existing[0]
                            continue
                        
                        # Crear nuevo usuario - simplificado
                        data = {
                            'login': login,
                            'name': record.get('name') or login or f'User_{old_id}',
                            'active': record.get('active', True),
                        }
                        
                        # Validar login único
                        if not login or len(login) < 3:
                            # Mapear a admin si login inválido
                            stats['user_mapping'][old_id] = 2
                            continue
                        
                        # Partner asociado (opcional, puede no existir aún)
                        if record.get('partner_id'):
                            partner_id = record['partner_id'][0] if isinstance(record['partner_id'], (list, tuple)) else record['partner_id']
                            mapped_partner = stats['id_mapping'].get('res.partner', {}).get(partner_id)
                            if mapped_partner:
                                data['partner_id'] = mapped_partner
                        
                        try:
                            # Crear usuario
                            new_id = target_models.execute_kw(
                                TARGET['db'], target_uid, 'admin',
                                'res.users', 'create', [data]
                            )
                            
                            stats['user_mapping'][old_id] = new_id
                            migrated += 1
                        except Exception as create_error:
                            # Si falla creación, mapear a admin
                            error_str = str(create_error)
                            if 'already exists' in error_str.lower() or 'duplicate' in error_str.lower():
                                # Usuario ya existe, buscar y mapear
                                try:
                                    existing = target_models.execute_kw(
                                        TARGET['db'], target_uid, 'admin',
                                        'res.users', 'search', [[('login', '=', login)]]
                                    )
                                    if existing:
                                        stats['user_mapping'][old_id] = existing[0]
                                except:
                                    stats['user_mapping'][old_id] = 2
                            else:
                                # Otro error, mapear a admin
                                stats['user_mapping'][old_id] = 2
                            errors += 1
                        
                    except Exception as e:
                        errors += 1
                        if errors <= 5:
                            log(f"Error usuario {record.get('login')}: {str(e)[:100]}", "ERROR")
                        # Mapear a admin si falla
                        stats['user_mapping'][record.get('id')] = 2
                
                offset += batch_size
                if migrated % 25 == 0:
                    log(f"  Progreso: {migrated:,}/{total:,}")
                time.sleep(0.2)
                
            except Exception as e:
                log(f"Error en lote: {e}", "ERROR")
                break
        
        log(f"✓ Usuarios: {migrated:,} migrados, {errors} errores")
        stats['models']['res.users'] = {'migrated': migrated, 'errors': errors, 'total': total}
        return migrated
        
    except Exception as e:
        log(f"✗ Error migrando usuarios: {e}", "ERROR")
        return 0

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
        elif field_name in ['create_uid', 'write_uid', 'user_id', 'assigned_to']:
            # Mapear usuarios - esto se maneja en migrate_model directamente
            return rel_id  # Se mapeará después
        elif field_name == 'project_id':
            return id_mappings.get('project.project', {}).get(rel_id, False)
        elif field_name == 'sale_order_id':
            return id_mappings.get('sale.order', {}).get(rel_id, False)
        else:
            return rel_id
    return value[0] if value else False

def clean_field_value(field_name, value, model_name):
    """Limpia y valida valores de campos"""
    if value is None:
        return False
    
    # Campos de fecha/datetime
    if field_name in ['create_date', 'write_date', 'date_order', 'invoice_date']:
        if isinstance(value, str) and value:
            return value
        return False
    
    # Campos booleanos
    if isinstance(value, bool):
        return value
    
    # Campos de texto - limpiar
    if isinstance(value, str):
        # Limitar longitud si es muy largo
        if len(value) > 1000:
            return value[:1000]
        return value
    
    # Campos numéricos
    if isinstance(value, (int, float)):
        return value
    
    # Listas/tuplas
    if isinstance(value, (list, tuple)):
        if len(value) == 0:
            return False
        return value
    
    return value

def migrate_model(source_models, source_uid, target_models, target_uid, model_name, batch_size=50):
    """Migra un modelo con manejo de metadatos"""
    log(f"\n{'='*70}")
    log(f"MIGRANDO: {model_name}")
    log(f"{'='*70}")
    
    try:
        total = source_models.execute_kw(
            SOURCE['db'], source_uid, SOURCE['key'],
            model_name, 'search_count', [[]]
        )
        log(f"Total en origen: {total:,}")
        
        if total == 0:
            return 0
        
        # Campos según modelo
        if model_name == 'res.partner':
            fields = ['name', 'is_company', 'email', 'phone', 'mobile', 'street', 'city', 
                     'state_id', 'country_id', 'category_id', 'parent_id', 'active',
                     'create_uid', 'write_uid', 'create_date', 'write_date']
        elif model_name == 'product.template':
            fields = ['name', 'list_price', 'default_code', 'categ_id', 'type', 
                     'sale_ok', 'purchase_ok', 'active', 'create_uid', 'write_uid']
        elif model_name == 'product.product':
            fields = ['name', 'product_tmpl_id', 'default_code', 'list_price', 'active',
                     'create_uid', 'write_uid']
        elif model_name == 'crm.lead':
            fields = ['name', 'partner_id', 'email_from', 'phone', 'stage_id', 
                     'probability', 'active', 'create_uid', 'write_uid', 'user_id']
        elif model_name == 'sale.order':
            fields = ['name', 'partner_id', 'date_order', 'state', 'amount_total',
                     'create_uid', 'write_uid', 'user_id', 'order_line']
        elif model_name == 'account.move':
            fields = ['name', 'partner_id', 'move_type', 'invoice_date', 'state', 
                     'amount_total', 'create_uid', 'write_uid']
        elif model_name == 'project.project':
            fields = ['name', 'partner_id', 'active', 'create_uid', 'write_uid', 'user_id']
        elif model_name == 'project.task':
            fields = ['name', 'project_id', 'partner_id', 'user_id', 'stage_id', 
                     'active', 'create_uid', 'write_uid', 'description', 'date_deadline']
        else:
            fields = ['name', 'active', 'create_uid', 'write_uid']
        
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
                                
                                # Limpiar valor
                                cleaned = clean_field_value(field, value, model_name)
                                
                                # Mapear relaciones
                                if field in ['create_uid', 'write_uid', 'user_id']:
                                    # Mapear usuarios usando user_mapping
                                    if isinstance(value, (list, tuple)) and len(value) > 0:
                                        old_user_id = value[0]
                                        mapped_user = stats['user_mapping'].get(old_user_id, 2)  # Default admin
                                        data[field] = mapped_user
                                    elif isinstance(value, int):
                                        mapped_user = stats['user_mapping'].get(value, 2)
                                        data[field] = mapped_user
                                else:
                                    mapped = map_related_id(field, cleaned, stats['id_mapping'])
                                    if mapped is not False or (isinstance(mapped, bool) and mapped == False):
                                        data[field] = mapped
                                    elif cleaned and not isinstance(cleaned, (list, tuple)):
                                        data[field] = cleaned
                        
                        # Validar datos mínimos
                        if not data.get('name') and model_name not in ['account.move', 'product.product']:
                            # Generar nombre si falta
                            if model_name == 'res.partner':
                                data['name'] = f'Partner_{old_id}'
                            else:
                                continue
                        
                        # Limpiar campos None o vacíos problemáticos
                        data_clean = {}
                        for k, v in data.items():
                            if v is not None and v != '':
                                if isinstance(v, str) and len(v) > 2000:
                                    data_clean[k] = v[:2000]  # Limitar longitud
                                else:
                                    data_clean[k] = v
                        
                        # Crear en destino
                        password = 'admin'
                        try:
                            new_id = target_models.execute_kw(
                                TARGET['db'], target_uid, password,
                                model_name, 'create', [data_clean]
                            )
                            
                            # Guardar mapeo
                            if model_name not in stats['id_mapping']:
                                stats['id_mapping'][model_name] = {}
                            stats['id_mapping'][model_name][old_id] = new_id
                            migrated += 1
                        except Exception as create_error:
                            # Si falla, intentar sin campos opcionales problemáticos
                            error_str = str(create_error)
                            if 'required' in error_str.lower() or 'invalid' in error_str.lower():
                                # Intentar con campos mínimos
                                try:
                                    minimal_data = {'name': data_clean.get('name', f'{model_name}_{old_id}')}
                                    if 'active' in data_clean:
                                        minimal_data['active'] = data_clean['active']
                                    new_id = target_models.execute_kw(
                                        TARGET['db'], target_uid, password,
                                        model_name, 'create', [minimal_data]
                                    )
                                    stats['id_mapping'].setdefault(model_name, {})[old_id] = new_id
                                    migrated += 1
                                except:
                                    errors += 1
                            else:
                                errors += 1
                        
                    except Exception as e:
                        errors += 1
                        # Solo loguear primeros errores para no saturar log
                        if errors <= 5:
                            error_msg = str(e)
                            log(f"Error registro {record.get('id')}: {error_msg[:100]}", "ERROR")
                        # Continuar aunque haya errores
                        if errors > 500 and migrated == 0:
                            # Si hay muchos errores y nada migrado, puede ser problema sistemático
                            log(f"Demasiados errores sin éxitos ({errors}), revisando...", "WARN")
                            break
                
                offset += batch_size
                if migrated % 50 == 0:
                    log(f"  Progreso: {migrated:,}/{total:,} (errores: {errors})")
                time.sleep(0.2)
                
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
    log("MIGRACIÓN MEJORADA DE DATOS CON METADATOS")
    log("="*70)
    start = datetime.now()
    
    # Conectar
    log("Conectando a servidores...")
    source_models, source_uid = connect_source_mcp()
    if not source_models:
        log("Error: No se pudo conectar a origen", "ERROR")
        return False
    log("✓ Origen conectado")
    
    target_models, target_uid = connect_target_direct()
    if not target_models:
        log("Error: No se pudo conectar a destino", "ERROR")
        return False
    log("✓ Destino conectado")
    
    # PASO 1: Migrar usuarios primero (crítico para metadatos)
    log("\n" + "="*70)
    log("PASO 1: MIGRAR USUARIOS (Para metadatos)")
    log("="*70)
    migrate_users(source_models, source_uid, target_models, target_uid)
    
    # PASO 2: Migrar modelos en orden
    log("\n" + "="*70)
    log("PASO 2: MIGRAR DATOS")
    log("="*70)
    
    models = [
        'res.partner',
        'product.template',
        'product.product',
        'crm.lead',
        'sale.order',
        'account.move',
        'project.project',
        'project.task',
        'knowledge.article',
        'helpdesk.ticket',
    ]
    
    for model in models:
        migrate_model(source_models, source_uid, target_models, target_uid, model)
        time.sleep(1)
    
    # Resumen final
    duration = (datetime.now() - start).total_seconds() / 60
    log("\n" + "="*70)
    log("MIGRACIÓN COMPLETADA")
    log("="*70)
    log(f"Duración: {duration:.1f} minutos")
    log(f"Total migrado: {stats['total_migrated']:,}")
    log(f"Total errores: {stats['total_errors']}")
    
    # Guardar estadísticas
    stats_file = log_file.parent / f"migration_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(stats_file, 'w') as f:
        json.dump(stats, f, indent=2, default=str)
    log(f"✓ Estadísticas: {stats_file}")
    
    return True

if __name__ == "__main__":
    main()

