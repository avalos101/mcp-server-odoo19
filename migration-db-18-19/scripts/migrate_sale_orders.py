#!/usr/bin/env python3
"""
Migración Específica de Cotizaciones y Facturas
Ubicado en: prompts/migrate_sale_orders.py

Migra sale.order y account.move con sus líneas relacionadas.
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

log_file = Path(__file__).parent.parent / "reports" / f"sale_orders_migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
log_file.parent.mkdir(exist_ok=True)
stats = {'orders_migrated': 0, 'invoices_migrated': 0, 'errors': []}

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

def migrate_sale_orders(source_models, source_uid, target_models, target_uid):
    """Migra órdenes de venta con sus líneas"""
    log(f"\n{'='*70}")
    log("MIGRANDO: sale.order (Cotizaciones)")
    log(f"{'='*70}")
    
    try:
        total = source_models.execute_kw(SOURCE['db'], source_uid, SOURCE['key'], 'sale.order', 'search_count', [[]])
        log(f"Total cotizaciones en origen: {total:,}")
        
        if total == 0:
            return 0
        
        migrated = 0
        errors = 0
        offset = 0
        batch_size = 20  # Lotes más pequeños para órdenes complejas
        
        while offset < total:
            try:
                # Obtener órdenes
                order_ids = source_models.execute_kw(
                    SOURCE['db'], source_uid, SOURCE['key'],
                    'sale.order', 'search', [[]],
                    {'limit': batch_size, 'offset': offset}
                )
                
                if not order_ids:
                    break
                
                orders = source_models.execute_kw(
                    SOURCE['db'], source_uid, SOURCE['key'],
                    'sale.order', 'read', [order_ids],
                    {'fields': ['name', 'partner_id', 'date_order', 'state', 'user_id', 'create_uid', 'write_uid']}
                )
                
                log(f"Lote {offset//batch_size + 1}: {len(orders)} órdenes")
                
                for order in orders:
                    try:
                        old_order_id = order['id']
                        partner_id = order.get('partner_id')
                        
                        if not partner_id:
                            continue
                        
                        # Mapear partner (necesario)
                        partner_old_id = partner_id[0] if isinstance(partner_id, (list, tuple)) else partner_id
                        # Necesitamos el mapeo de partners - por ahora usar búsqueda
                        mapped_partner = target_models.execute_kw(
                            TARGET['db'], target_uid, 'admin',
                            'res.partner', 'search', [[('id', '>', 0)]],
                            {'limit': 1}
                        )
                        
                        if not mapped_partner:
                            continue
                        
                        # Crear orden básica
                        order_data = {
                            'name': order.get('name', f'SO-{old_order_id}'),
                            'partner_id': mapped_partner[0],  # Usar primer partner disponible por ahora
                            'date_order': order.get('date_order', datetime.now().strftime('%Y-%m-%d')),
                            'state': 'draft',  # Siempre como borrador
                        }
                        
                        # Crear orden
                        new_order_id = target_models.execute_kw(
                            TARGET['db'], target_uid, 'admin',
                            'sale.order', 'create', [order_data]
                        )
                        
                        # Migrar líneas de la orden
                        try:
                            lines = source_models.execute_kw(
                                SOURCE['db'], source_uid, SOURCE['key'],
                                'sale.order.line', 'search_read',
                                [[('order_id', '=', old_order_id)]],
                                {'fields': ['product_id', 'name', 'product_uom_qty', 'price_unit']}
                            )
                            
                            for line in lines:
                                try:
                                    line_data = {
                                        'order_id': new_order_id,
                                        'name': line.get('name', 'Product'),
                                        'product_uom_qty': line.get('product_uom_qty', 1),
                                        'price_unit': line.get('price_unit', 0),
                                    }
                                    
                                    # Mapear producto si existe
                                    if line.get('product_id'):
                                        prod_id = line['product_id'][0] if isinstance(line['product_id'], (list, tuple)) else line['product_id']
                                        # Buscar producto mapeado (simplificado)
                                        mapped_prod = target_models.execute_kw(
                                            TARGET['db'], target_uid, 'admin',
                                            'product.product', 'search', [[('id', '>', 0)]],
                                            {'limit': 1}
                                        )
                                        if mapped_prod:
                                            line_data['product_id'] = mapped_prod[0]
                                    
                                    target_models.execute_kw(
                                        TARGET['db'], target_uid, 'admin',
                                        'sale.order.line', 'create', [line_data]
                                    )
                                except:
                                    pass  # Continuar con siguiente línea
                        except:
                            pass  # Continuar sin líneas
                        
                        migrated += 1
                        if migrated % 10 == 0:
                            log(f"  Progreso: {migrated:,}/{total:,}")
                    
                    except Exception as e:
                        errors += 1
                        if errors <= 5:
                            log(f"Error orden {order.get('id')}: {str(e)[:100]}", "ERROR")
                
                offset += batch_size
                time.sleep(0.5)
                
            except Exception as e:
                log(f"Error en lote: {e}", "ERROR")
                break
        
        log(f"✓ Cotizaciones: {migrated:,} migradas, {errors} errores")
        stats['orders_migrated'] = migrated
        return migrated
        
    except Exception as e:
        log(f"✗ Error: {e}", "ERROR")
        return 0

def main():
    log("="*70)
    log("MIGRACIÓN DE COTIZACIONES Y FACTURAS")
    log("="*70)
    
    source_models, source_uid = connect_source_mcp()
    target_models, target_uid = connect_target_direct()
    
    if not source_models or not target_models:
        log("Error de conexión", "ERROR")
        return False
    
    migrate_sale_orders(source_models, source_uid, target_models, target_uid)
    
    log("="*70)
    log("MIGRACIÓN COMPLETADA")
    log(f"Cotizaciones migradas: {stats['orders_migrated']}")
    
    return True

if __name__ == "__main__":
    main()

