#!/usr/bin/env python3
"""
Migración de Datos Pendientes: Facturas y Tareas
Ubicado en: prompts/migrate_pending_data.py

Migra los datos que quedaron pendientes:
- account.move (Facturas)
- project.task (Tareas) - con corrección de campos
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

log_file = Path(__file__).parent.parent / "reports" / f"pending_migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
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
            return (models, uid)
    except Exception as e:
        log(f"Error conexión destino: {str(e)[:100]}", "WARN")
    return None, None

def migrate_invoices(source_models, source_uid, target_models, target_uid):
    """Migra facturas (account.move)"""
    log(f"\n{'='*70}")
    log("MIGRANDO: account.move (Facturas)")
    log(f"{'='*70}")
    
    try:
        total = source_models.execute_kw(SOURCE['db'], source_uid, SOURCE['key'], 'account.move', 'search_count', [[]])
        log(f"Total facturas en origen: {total:,}")
        
        if total == 0:
            return 0
        
        # Campos básicos para facturas
        fields = ['name', 'partner_id', 'move_type', 'invoice_date', 'date', 'state', 
                 'amount_total', 'amount_untaxed', 'amount_tax', 'currency_id',
                 'invoice_line_ids', 'create_uid', 'write_uid']
        
        migrated = 0
        errors = 0
        offset = 0
        batch_size = 10  # Lotes pequeños para facturas
        
        while offset < total:
            try:
                records = source_models.execute_kw(
                    SOURCE['db'], source_uid, SOURCE['key'],
                    'account.move', 'search_read',
                    [[]],
                    {'fields': fields, 'limit': batch_size, 'offset': offset}
                )
                
                if not records:
                    break
                
                log(f"Lote {offset//batch_size + 1}: {len(records)} facturas")
                
                for record in records:
                    try:
                        data = {
                            'name': record.get('name'),
                            'move_type': record.get('move_type', 'out_invoice'),
                            'state': 'draft',  # Crear como borrador
                        }
                        
                        # Partner
                        if record.get('partner_id'):
                            partner_id = record['partner_id'][0] if isinstance(record['partner_id'], (list, tuple)) else record['partner_id']
                            # Verificar si está mapeado
                            mapped_partner = stats['id_mapping'].get('res.partner', {}).get(partner_id)
                            if mapped_partner:
                                data['partner_id'] = mapped_partner
                            else:
                                log(f"  Partner {partner_id} no mapeado, saltando factura {record.get('id')}", "WARN")
                                errors += 1
                                continue
                        
                        # Fechas
                        if record.get('invoice_date'):
                            data['invoice_date'] = record['invoice_date']
                        elif record.get('date'):
                            data['date'] = record['date']
                        
                        # Montos
                        if record.get('amount_total'):
                            data['amount_total'] = record['amount_total']
                        
                        # Crear factura
                        password = 'admin'
                        new_id = target_models.execute_kw(
                            TARGET['db'], target_uid, password,
                            'account.move', 'create', [data]
                        )
                        
                        # Guardar mapeo
                        if 'account.move' not in stats['id_mapping']:
                            stats['id_mapping']['account.move'] = {}
                        stats['id_mapping']['account.move'][record['id']] = new_id
                        migrated += 1
                        
                        log(f"  ✓ Factura {record.get('name')} migrada (ID: {new_id})")
                        
                    except Exception as e:
                        errors += 1
                        if errors <= 5:
                            log(f"Error factura {record.get('id')}: {str(e)[:150]}", "ERROR")
                
                offset += batch_size
                time.sleep(0.5)
                
            except Exception as e:
                log(f"Error en lote: {e}", "ERROR")
                break
        
        log(f"✓ Facturas: {migrated:,} migradas, {errors} errores")
        stats['models']['account.move'] = {'migrated': migrated, 'errors': errors, 'total': total}
        return migrated
        
    except Exception as e:
        log(f"✗ Error: {e}", "ERROR")
        return 0

def migrate_tasks(source_models, source_uid, target_models, target_uid):
    """Migra tareas (project.task) con campos corregidos"""
    log(f"\n{'='*70}")
    log("MIGRANDO: project.task (Tareas) - CON CORRECCIÓN")
    log(f"{'='*70}")
    
    try:
        total = source_models.execute_kw(SOURCE['db'], source_uid, SOURCE['key'], 'project.task', 'search_count', [[]])
        log(f"Total tareas en origen: {total:,}")
        
        if total == 0:
            return 0
        
        # Verificar campos disponibles en destino
        try:
            target_fields = target_models.execute_kw(TARGET['db'], target_uid, 'admin', 'project.task', 'fields_get', [], {'attributes': ['string', 'type']})
            assignee_field = None
            for field_name in ['user_ids', 'assignee_ids', 'user_id', 'assigned_to']:
                if field_name in target_fields:
                    assignee_field = field_name
                    log(f"Campo de asignación encontrado: {assignee_field}")
                    break
        except:
            assignee_field = 'user_ids'  # Default para Odoo 19
        
        # Campos para tareas
        fields = ['name', 'project_id', 'partner_id', 'stage_id', 'active', 
                 'create_uid', 'write_uid', 'description']
        
        # Agregar campo de usuario si existe en origen
        if 'user_id' in source_models.execute_kw(SOURCE['db'], source_uid, SOURCE['key'], 'project.task', 'fields_get', [], {}):
            fields.append('user_id')
        
        migrated = 0
        errors = 0
        offset = 0
        batch_size = 50
        
        while offset < total:
            try:
                records = source_models.execute_kw(
                    SOURCE['db'], source_uid, SOURCE['key'],
                    'project.task', 'search_read',
                    [[]],
                    {'fields': fields, 'limit': batch_size, 'offset': offset}
                )
                
                if not records:
                    break
                
                log(f"Lote {offset//batch_size + 1}: {len(records)} tareas")
                
                for record in records:
                    try:
                        data = {
                            'name': record.get('name') or f'Task_{record.get("id")}',
                            'active': record.get('active', True),
                        }
                        
                        # Proyecto
                        if record.get('project_id'):
                            project_id = record['project_id'][0] if isinstance(record['project_id'], (list, tuple)) else record['project_id']
                            mapped_project = stats['id_mapping'].get('project.project', {}).get(project_id)
                            if mapped_project:
                                data['project_id'] = mapped_project
                            else:
                                log(f"  Proyecto {project_id} no mapeado, saltando tarea {record.get('id')}", "WARN")
                                errors += 1
                                continue
                        
                        # Partner
                        if record.get('partner_id'):
                            partner_id = record['partner_id'][0] if isinstance(record['partner_id'], (list, tuple)) else record['partner_id']
                            mapped_partner = stats['id_mapping'].get('res.partner', {}).get(partner_id)
                            if mapped_partner:
                                data['partner_id'] = mapped_partner
                        
                        # Stage
                        if record.get('stage_id'):
                            stage_id = record['stage_id'][0] if isinstance(record['stage_id'], (list, tuple)) else record['stage_id']
                            # Intentar mapear stage, si no existe usar False
                            data['stage_id'] = stage_id  # Odoo puede crear stages automáticamente
                        
                        # Descripción
                        if record.get('description'):
                            data['description'] = record['description'][:5000] if len(record['description']) > 5000 else record['description']
                        
                        # Usuario asignado - usar campo correcto para Odoo 19
                        if record.get('user_id') and assignee_field:
                            user_id = record['user_id'][0] if isinstance(record['user_id'], (list, tuple)) else record['user_id']
                            # Mapear usuario si tenemos el mapeo
                            mapped_user = stats.get('user_mapping', {}).get(user_id, 2)  # Default admin
                            if assignee_field == 'user_ids':
                                data['user_ids'] = [(6, 0, [mapped_user])]  # Many2many
                            elif assignee_field == 'assignee_ids':
                                data['assignee_ids'] = [(6, 0, [mapped_user])]
                            else:
                                data[assignee_field] = mapped_user
                        
                        # Crear tarea
                        password = 'admin'
                        new_id = target_models.execute_kw(
                            TARGET['db'], target_uid, password,
                            'project.task', 'create', [data]
                        )
                        
                        # Guardar mapeo
                        if 'project.task' not in stats['id_mapping']:
                            stats['id_mapping']['project.task'] = {}
                        stats['id_mapping']['project.task'][record['id']] = new_id
                        migrated += 1
                        
                    except Exception as e:
                        errors += 1
                        if errors <= 10:
                            log(f"Error tarea {record.get('id')}: {str(e)[:150]}", "ERROR")
                
                offset += batch_size
                if migrated % 25 == 0:
                    log(f"  Progreso: {migrated:,}/{total:,}")
                time.sleep(0.3)
                
            except Exception as e:
                log(f"Error en lote: {e}", "ERROR")
                break
        
        log(f"✓ Tareas: {migrated:,} migradas, {errors} errores")
        stats['models']['project.task'] = {'migrated': migrated, 'errors': errors, 'total': total}
        return migrated
        
    except Exception as e:
        log(f"✗ Error: {e}", "ERROR")
        return 0

def load_existing_mappings():
    """Carga mapeos existentes desde archivo JSON si existe"""
    mapping_file = Path(__file__).parent.parent / "reports" / "migration_stats_20251209_145454.json"
    if mapping_file.exists():
        try:
            with open(mapping_file, 'r') as f:
                data = json.load(f)
                if 'id_mapping' in data:
                    stats['id_mapping'] = data['id_mapping']
                    log(f"✓ Mapeos cargados desde {mapping_file.name}")
        except:
            pass

def main():
    log("="*70)
    log("MIGRACIÓN DE DATOS PENDIENTES")
    log("="*70)
    start = datetime.now()
    
    # Cargar mapeos existentes
    load_existing_mappings()
    
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
    
    # Migrar pendientes
    migrate_invoices(source_models, source_uid, target_models, target_uid)
    time.sleep(2)
    migrate_tasks(source_models, source_uid, target_models, target_uid)
    
    # Resumen
    duration = (datetime.now() - start).total_seconds() / 60
    log("\n" + "="*70)
    log("MIGRACIÓN PENDIENTES COMPLETADA")
    log("="*70)
    log(f"Duración: {duration:.1f} minutos")
    log(f"Total migrado: {stats['total_migrated']}")
    
    return True

if __name__ == "__main__":
    main()

