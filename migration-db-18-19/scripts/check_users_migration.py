#!/usr/bin/env python3
"""
Verificación de Usuarios Migrados
Ubicado en: prompts/check_users_migration.py

Verifica qué usuarios existen en ambas bases de datos.
"""

import subprocess
import xmlrpc.client
import ssl
import urllib.request
from datetime import datetime

SOURCE = {
    'ssh': 'diego.avalos@omnierp.app',
    'db': 'omnierp.app',
    'url': 'https://omnierp.app',
    'user': 'admin@omnierp.app',
    'key': '7f3ea49d0339de71e39996866b61c26416ba0597'
}

TARGET = {
    'ssh': 'diego.avalos@laia.one',
    'db': 'omnierp_migrated',
    'url': 'https://laia.one',
    'user': 'admin@laia.one',
    'key': 'cfebea4c6d0a3cc3e345db4aa9c94b3e085ea3e5'
}

def ssh_exec(cmd, host):
    ssh_cmd = ['ssh', '-o', 'StrictHostKeyChecking=no', host, cmd]
    try:
        result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=60)
        return result.returncode == 0, result.stdout, result.stderr
    except:
        return False, "", ""

def get_users_via_sql(ssh, db):
    """Obtiene usuarios vía SQL"""
    cmd = f"sudo -u postgres psql -d '{db}' -t -c \"SELECT u.id, u.login, p.name, u.active FROM res_users u LEFT JOIN res_partner p ON u.partner_id = p.id ORDER BY u.id LIMIT 20;\""
    success, out, err = ssh_exec(cmd, ssh)
    if success:
        users = []
        for line in out.strip().split('\n'):
            if line.strip():
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 4:
                    users.append({
                        'id': parts[0],
                        'login': parts[1],
                        'name': parts[2] if len(parts) > 2 else '',
                        'active': parts[3] if len(parts) > 3 else 'True'
                    })
        return users
    return []

def get_users_via_mcp(url, db, user, key):
    """Obtiene usuarios vía MCP"""
    try:
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
        
        transport = DatabaseAwareTransport(db)
        common = xmlrpc.client.ServerProxy(f"{url}/mcp/xmlrpc/common", transport=transport, allow_none=True)
        models = xmlrpc.client.ServerProxy(f"{url}/mcp/xmlrpc/object", transport=transport, allow_none=True)
        uid = common.authenticate(db, user, key, {})
        
        if uid:
            users = models.execute_kw(db, uid, key, 'res.users', 'search_read', [[]], {'fields': ['id', 'login', 'name', 'active'], 'limit': 20})
            return users
    except Exception as e:
        print(f"Error MCP: {e}")
    return None

def main():
    print("="*70)
    print("VERIFICACIÓN DE USUARIOS")
    print("="*70)
    
    print("\nSERVIDOR ORIGEN (OmniERP):")
    print("-"*70)
    source_users = get_users_via_sql(SOURCE['ssh'], SOURCE['db'])
    print(f"Total usuarios encontrados: {len(source_users)}")
    print("\nPrimeros usuarios:")
    for u in source_users[:10]:
        print(f"  ID: {u['id']:>4} | Login: {u['login']:<30} | Nombre: {u['name']:<30} | Activo: {u['active']}")
    
    # Intentar vía MCP también
    print("\nIntentando obtener usuarios vía MCP...")
    source_users_mcp = get_users_via_mcp(SOURCE['url'], SOURCE['db'], SOURCE['user'], SOURCE['key'])
    if source_users_mcp:
        print(f"✓ Obtenidos {len(source_users_mcp)} usuarios vía MCP")
    
    print("\nSERVIDOR DESTINO (Laia.one - omnierp_migrated):")
    print("-"*70)
    target_users = get_users_via_sql(TARGET['ssh'], TARGET['db'])
    print(f"Total usuarios encontrados: {len(target_users)}")
    print("\nUsuarios en nueva BD:")
    for u in target_users:
        print(f"  ID: {u['id']:>4} | Login: {u['login']:<30} | Nombre: {u['name']:<30} | Activo: {u['active']}")
    
    print("\n" + "="*70)
    print("RESUMEN:")
    print("="*70)
    print(f"Usuarios en origen: {len(source_users)}")
    print(f"Usuarios en destino: {len(target_users)}")
    print(f"\n⚠ Los usuarios NO fueron migrados automáticamente")
    print(f"  La nueva BD solo tiene los usuarios por defecto de Odoo")
    print(f"\nPara acceder a la nueva BD:")
    print(f"  - Usuario: admin (ID: 2)")
    print(f"  - Contraseña: La misma que se configuró al inicializar la BD")
    print(f"  - O usar: admin@laia.one (si se configuró igual que admin-laia)")

if __name__ == "__main__":
    main()

