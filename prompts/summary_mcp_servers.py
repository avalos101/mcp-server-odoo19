#!/usr/bin/env python3
"""
Resumen de Servidores MCP Configurados
Ubicado en: prompts/summary_mcp_servers.py

Este script consulta todos los servidores MCP configurados y genera
un resumen con información detallada de cada uno.
"""

import xmlrpc.client
import ssl
import urllib.request
import urllib.error
import json
from datetime import datetime

# Configuración de servidores
SERVERS = {
    "admin.controltotal.cloud": {
        "url": "https://admin.app.controltotal.cloud",
        "db": "admin_saas",
        "user": "admin@omnierp.app",
        "api_key": "73c3c82596667e2251d374cd5051a3415012683f",
        "name": "ControlTotal Cloud"
    },
    "laia.one": {
        "url": "https://laia.one",
        "db": "admin-laia",
        "user": "admin@laia.one",
        "api_key": "cfebea4c6d0a3cc3e345db4aa9c94b3e085ea3e5",
        "name": "Laia.one"
    },
    "omnierp": {
        "url": "https://omnierp.app",
        "db": "omnierp.app",
        "user": "admin@omnierp.app",
        "api_key": "7f3ea49d0339de71e39996866b61c26416ba0597",
        "name": "OmniERP"
    }
}


class DatabaseAwareTransport(xmlrpc.client.SafeTransport):
    """Transport personalizado que envía el header X-Odoo-Database"""
    def __init__(self, database, use_datetime=False, use_builtin_types=False):
        super().__init__(use_datetime=use_datetime, use_builtin_types=use_builtin_types)
        self.database = database
        self.verbose = False
    
    def request(self, host, handler, request_body, verbose=False):
        """Override request para agregar el header de base de datos"""
        self.verbose = verbose
        if not handler.startswith('http'):
            handler = 'https://%s%s' % (host, handler)
        
        req = urllib.request.Request(handler, data=request_body)
        req.add_header('Content-Type', 'text/xml')
        req.add_header('X-Odoo-Database', self.database)
        
        try:
            context = ssl._create_unverified_context()
            with urllib.request.urlopen(req, context=context) as response:
                return self.parse_response(response)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                req2 = urllib.request.Request(handler, data=request_body)
                req2.add_header('Content-Type', 'text/xml')
                with urllib.request.urlopen(req2, context=context) as response:
                    return self.parse_response(response)
            raise


def get_server_info(server_key, config):
    """Obtiene información detallada de un servidor"""
    print(f"\n{'='*70}")
    print(f"Consultando: {config['name']} ({server_key})")
    print(f"{'='*70}")
    
    info = {
        "name": config['name'],
        "domain": config['url'].replace('https://', '').replace('http://', ''),
        "url": config['url'],
        "database": config['db'],
        "user": config['user'],
        "status": "Desconectado",
        "odoo_version": "N/A",
        "mcp_version": "N/A",
        "uid": None,
        "stats": {}
    }
    
    try:
        context = ssl._create_unverified_context()
        common_url = f"{config['url']}/mcp/xmlrpc/common"
        object_url = f"{config['url']}/mcp/xmlrpc/object"
        
        # Probar health endpoint
        health_url = f"{config['url']}/mcp/health"
        try:
            req = urllib.request.Request(health_url)
            req.add_header('X-Odoo-Database', config['db'])
            with urllib.request.urlopen(req, context=context, timeout=10) as response:
                health_data = json.loads(response.read().decode('utf-8'))
                if health_data.get('success'):
                    info['mcp_version'] = health_data.get('data', {}).get('mcp_server_version', 'N/A')
                    info['status'] = "Conectado"
        except:
            try:
                req2 = urllib.request.Request(health_url)
                with urllib.request.urlopen(req2, context=context, timeout=10) as response:
                    health_data = json.loads(response.read().decode('utf-8'))
                    if health_data.get('success'):
                        info['mcp_version'] = health_data.get('data', {}).get('mcp_server_version', 'N/A')
                        info['status'] = "Conectado"
            except:
                pass
        
        # Conectar vía XML-RPC
        transport = DatabaseAwareTransport(config['db'], use_datetime=True)
        common = xmlrpc.client.ServerProxy(common_url, transport=transport, allow_none=True)
        models = xmlrpc.client.ServerProxy(object_url, transport=transport, allow_none=True)
        
        # Autenticar
        uid = common.authenticate(config['db'], config['user'], config['api_key'], {})
        
        if uid:
            info['uid'] = uid
            info['status'] = "Conectado"
            print(f"✓ Conexión exitosa (UID: {uid})")
            
            # Obtener versión de Odoo
            try:
                version_info = models.execute_kw(
                    config['db'], uid, config['api_key'],
                    'ir.module.module', 'search_read',
                    [[('name', '=', 'base')]],
                    {'fields': ['latest_version'], 'limit': 1}
                )
                if version_info:
                    info['odoo_version'] = version_info[0].get('latest_version', 'N/A')
            except:
                pass
            
            # Obtener estadísticas
            try:
                # Productos
                total_products = models.execute_kw(
                    config['db'], uid, config['api_key'],
                    'product.product', 'search_count', [[]]
                )
                info['stats']['productos'] = total_products
                
                # Partners
                total_partners = models.execute_kw(
                    config['db'], uid, config['api_key'],
                    'res.partner', 'search_count', [[]]
                )
                info['stats']['partners'] = total_partners
                
                # Leads (si está disponible)
                try:
                    total_leads = models.execute_kw(
                        config['db'], uid, config['api_key'],
                        'crm.lead', 'search_count', [[]]
                    )
                    info['stats']['leads'] = total_leads
                except:
                    info['stats']['leads'] = "N/A"
                
                # Modelos MCP habilitados
                try:
                    enabled_models = models.execute_kw(
                        config['db'], uid, config['api_key'],
                        'mcp.enabled.model', 'search_count',
                        [[('active', '=', True)]]
                    )
                    info['stats']['modelos_mcp'] = enabled_models
                except:
                    info['stats']['modelos_mcp'] = "N/A"
                    
            except Exception as e:
                print(f"  ⚠ Error al obtener estadísticas: {e}")
                
        else:
            print("✗ Error de autenticación")
            
    except Exception as e:
        print(f"✗ Error de conexión: {e}")
        info['status'] = f"Error: {str(e)[:50]}"
    
    return info


def print_summary(servers_info):
    """Imprime un resumen formateado de todos los servidores"""
    print("\n" + "="*70)
    print("RESUMEN DE SERVIDORES MCP CONFIGURADOS")
    print("="*70)
    print(f"\nFecha de consulta: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total de servidores: {len(servers_info)}\n")
    
    for i, info in enumerate(servers_info, 1):
        print(f"\n{'─'*70}")
        print(f"SERVIDOR {i}: {info['name']}")
        print(f"{'─'*70}")
        print(f"  Dominio:              {info['domain']}")
        print(f"  URL:                  {info['url']}")
        print(f"  Base de datos:        {info['database']}")
        print(f"  Usuario:              {info['user']}")
        print(f"  Estado:               {info['status']}")
        print(f"  Versión Odoo:         {info['odoo_version']}")
        print(f"  Versión MCP:          {info['mcp_version']}")
        if info['uid']:
            print(f"  UID de sesión:        {info['uid']}")
        
        if info['stats']:
            print(f"\n  Estadísticas:")
            for key, value in info['stats'].items():
                label = key.replace('_', ' ').title()
                print(f"    - {label}: {value}")
    
    print(f"\n{'─'*70}")
    print("FIN DEL RESUMEN")
    print(f"{'─'*70}\n")


def main():
    """Función principal"""
    print("\n" + "="*70)
    print("CONSULTA DE SERVIDORES MCP")
    print("="*70)
    
    servers_info = []
    
    for server_key, config in SERVERS.items():
        info = get_server_info(server_key, config)
        servers_info.append(info)
    
    print_summary(servers_info)
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())

