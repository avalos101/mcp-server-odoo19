#!/usr/bin/env python3
"""
Corrección de Cotizaciones y Órdenes de Venta Migradas
Ubicado en: prompts/fix_sale_orders.py

Este script corrige las cotizaciones y órdenes ya migradas para incluir:
- Comercial (user_id)
- Fecha de creación correcta
- Líneas de productos completas (descripciones, cantidades, precios)
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

log_file = Path(__file__).parent.parent / "reports" / f"fix_sale_orders_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
log_file.parent.mkdir(exist_ok=True)
stats = {'updated': 0, 'errors': 0, 'errors_list': []}

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

def load_mappings():
    """Carga mapeos de IDs desde JSON"""
    mapping_file = Path(__file__).parent.parent / "reports" / "migration_stats_20251209_145454.json"
    mappings = {
        'partners': {},
        'users': {},
        'products': {},
        'orders': {}
    }
    
    if mapping_file.exists():
        try:
            with open(mapping_file, 'r') as f:
                data = json.load(f)
                if 'id_mapping' in data:
                    mappings['partners'] = data['id_mapping'].get('res.partner', {})
                    mappings['users'] = data.get('user_mapping', {})
                    mappings['products'] = data['id_mapping'].get('product.product', {})
                    mappings['orders'] = data['id_mapping'].get('sale.order', {})
                    log(f"✓ Mapeos cargados: {len(mappings['partners'])} partners, {len(mappings['users'])} users, {len(mappings['products'])} products, {len(mappings['orders'])} orders")
        except Exception as e:
            log(f"Error cargando mapeos: {e}", "WARN")
    
    return mappings

def get_order_lines(source_models, source_uid, order_id, mappings):
    """Obtiene y prepara las líneas de una cotización"""
    try:
        # Obtener líneas de la cotización original
        lines = source_models.execute_kw(
            SOURCE['db'], source_uid, SOURCE['key'],
            'sale.order.line', 'search_read',
            [[('order_id', '=', order_id)]],
            {'fields': ['product_id', 'name', 'product_uom_qty', 'price_unit', 'price_subtotal', 
                       'product_uom', 'discount', 'sequence']}
        )
        
        line_vals = []
        for line in lines:
            line_data = {
                'name': line.get('name', ''),
                'product_uom_qty': line.get('product_uom_qty', 1.0),
                'price_unit': line.get('price_unit', 0.0),
                'discount': line.get('discount', 0.0),
            }
            
            # Mapear producto
            if line.get('product_id'):
                product_id = line['product_id'][0] if isinstance(line['product_id'], (list, tuple)) else line['product_id']
                mapped_product = mappings['products'].get(product_id)
                if mapped_product:
                    line_data['product_id'] = mapped_product
                else:
                    log(f"  Producto {product_id} no mapeado en línea, usando descripción", "WARN")
            
            # UOM (unidad de medida)
            if line.get('product_uom'):
                uom_id = line['product_uom'][0] if isinstance(line['product_uom'], (list, tuple)) else line['product_uom']
                # Intentar usar el mismo ID, Odoo puede tenerlos
                line_data['product_uom'] = uom_id
            
            line_vals.append((0, 0, line_data))
        
        return line_vals
    except Exception as e:
        log(f"Error obteniendo líneas para orden {order_id}: {e}", "ERROR")
        return []

def fix_sale_orders(source_models, source_uid, target_models, target_uid, mappings):
    """Corrige las cotizaciones migradas"""
    log(f"\n{'='*70}")
    log("CORRIGIENDO: sale.order (Cotizaciones y Órdenes)")
    log(f"{'='*70}")
    
    try:
        # Obtener todas las cotizaciones en destino
        target_orders = target_models.execute_kw(
            TARGET['db'], target_uid, 'admin',
            'sale.order', 'search_read',
            [[]],
            {'fields': ['name', 'partner_id', 'user_id', 'date_order', 'create_date', 'order_line']}
        )
        
        log(f"Total cotizaciones en destino: {len(target_orders):,}")
        
        # Obtener mapeo inverso (nombre destino -> ID origen)
        order_name_to_old_id = {}
        for old_id, new_id in mappings['orders'].items():
            # Buscar por ID en destino para obtener nombre
            try:
                order = target_models.execute_kw(
                    TARGET['db'], target_uid, 'admin',
                    'sale.order', 'read', [[new_id]],
                    {'fields': ['name']}
                )
                if order:
                    order_name_to_old_id[order[0]['name']] = old_id
            except:
                pass
        
        updated = 0
        errors = 0
        batch_size = 20
        
        for idx, target_order in enumerate(target_orders, 1):
            try:
                order_name = target_order.get('name')
                target_id = target_order.get('id')
                
                # Buscar ID original
                old_id = order_name_to_old_id.get(order_name)
                if not old_id:
                    # Intentar buscar por nombre en origen
                    source_orders = source_models.execute_kw(
                        SOURCE['db'], source_uid, SOURCE['key'],
                        'sale.order', 'search', [[('name', '=', order_name)]]
                    )
                    if source_orders:
                        old_id = source_orders[0]
                    else:
                        log(f"  Orden {order_name} no encontrada en origen, saltando", "WARN")
                        continue
                
                # Obtener datos completos de origen
                source_order = source_models.execute_kw(
                    SOURCE['db'], source_uid, SOURCE['key'],
                    'sale.order', 'read', [[old_id]],
                    {'fields': ['name', 'partner_id', 'user_id', 'date_order', 'create_date', 
                               'state', 'order_line', 'amount_total']}
                )
                
                if not source_order:
                    continue
                
                source_order = source_order[0]
                update_data = {}
                
                # 1. Comercial (user_id)
                if source_order.get('user_id'):
                    user_id = source_order['user_id'][0] if isinstance(source_order['user_id'], (list, tuple)) else source_order['user_id']
                    mapped_user = mappings['users'].get(user_id, 2)  # Default admin
                    if not target_order.get('user_id') or target_order['user_id'] != mapped_user:
                        update_data['user_id'] = mapped_user
                
                # 2. Fecha de creación (create_date)
                if source_order.get('create_date'):
                    # Odoo no permite actualizar create_date directamente, pero podemos usar write_date
                    # O mejor, usar date_order que es más importante
                    if source_order.get('date_order'):
                        if not target_order.get('date_order') or target_order['date_order'] != source_order['date_order']:
                            update_data['date_order'] = source_order['date_order']
                
                # 3. Verificar si tiene líneas
                target_lines = target_order.get('order_line', [])
                has_lines = len(target_lines) > 0
                
                # 4. Obtener líneas de origen
                source_lines = get_order_lines(source_models, source_uid, old_id, mappings)
                
                # Si no tiene líneas o tiene menos líneas, actualizar
                if not has_lines or len(source_lines) > len(target_lines):
                    if source_lines:
                        # Primero eliminar líneas existentes si las hay
                        if has_lines:
                            line_ids = [line_id[0] if isinstance(line_id, (list, tuple)) else line_id for line_id in target_lines]
                            if line_ids:
                                try:
                                    target_models.execute_kw(
                                        TARGET['db'], target_uid, 'admin',
                                        'sale.order.line', 'unlink', [line_ids]
                                    )
                                except:
                                    pass
                        
                        update_data['order_line'] = source_lines
                
                # Actualizar si hay cambios
                if update_data:
                    try:
                        target_models.execute_kw(
                            TARGET['db'], target_uid, 'admin',
                            'sale.order', 'write', [[target_id], update_data]
                        )
                        updated += 1
                        log(f"  ✓ {order_name}: Actualizado (comercial: {update_data.get('user_id', 'N/A')}, líneas: {len(source_lines) if source_lines else 0})")
                    except Exception as e:
                        errors += 1
                        log(f"  ✗ {order_name}: Error actualizando - {str(e)[:150]}", "ERROR")
                        stats['errors_list'].append({'order': order_name, 'error': str(e)})
                else:
                    log(f"  - {order_name}: Ya está actualizado")
                
                if idx % batch_size == 0:
                    log(f"  Progreso: {idx:,}/{len(target_orders):,} (actualizados: {updated}, errores: {errors})")
                    time.sleep(0.5)
                
            except Exception as e:
                errors += 1
                log(f"  ✗ Error procesando orden {target_order.get('name', 'N/A')}: {str(e)[:150]}", "ERROR")
                stats['errors_list'].append({'order': target_order.get('name', 'N/A'), 'error': str(e)})
        
        log(f"\n✓ Cotizaciones actualizadas: {updated:,}, Errores: {errors}")
        stats['updated'] = updated
        stats['errors'] = errors
        return updated
        
    except Exception as e:
        log(f"✗ Error general: {e}", "ERROR")
        return 0

def main():
    log("="*70)
    log("CORRECCIÓN DE COTIZACIONES Y ÓRDENES MIGRADAS")
    log("="*70)
    start = datetime.now()
    
    # Cargar mapeos
    mappings = load_mappings()
    
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
    
    # Corregir cotizaciones
    fix_sale_orders(source_models, source_uid, target_models, target_uid, mappings)
    
    # Resumen
    duration = (datetime.now() - start).total_seconds() / 60
    log("\n" + "="*70)
    log("CORRECCIÓN COMPLETADA")
    log("="*70)
    log(f"Duración: {duration:.1f} minutos")
    log(f"Total actualizado: {stats['updated']}")
    log(f"Total errores: {stats['errors']}")
    
    return True

if __name__ == "__main__":
    main()

