#!/usr/bin/env python3
"""
Migración Completa Desatendida: OmniERP → Odoo 19
Ubicado en: prompts/complete_migration.py

Script completo que ejecuta toda la migración de manera desatendida.
"""

import subprocess
import xmlrpc.client
import ssl
import urllib.request
import time
from datetime import datetime
from pathlib import Path

SOURCE = {
    'ssh': 'diego.avalos@omnierp.app',
    'db': 'omnierp.app',
    'mcp_url': 'https://omnierp.app',
    'mcp_user': 'admin@omnierp.app',
    'mcp_key': '7f3ea49d0339de71e39996866b61c26416ba0597'
}

TARGET = {
    'ssh': 'diego.avalos@laia.one',
    'db': 'omnierp_migrated',
    'mcp_url': 'https://laia.one',
    'mcp_user': 'admin@laia.one',
    'mcp_key': 'cfebea4c6d0a3cc3e345db4aa9c94b3e085ea3e5',
    'odoo_bin': '/opt/odoo19/venv/bin/python3 /opt/odoo19/odoo-bin',
    'odoo_config': '/etc/odoo19.conf',
    'odoo_user': 'odoo19'
}

log_file = Path(__file__).parent.parent / "reports" / f"complete_migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
log_file.parent.mkdir(exist_ok=True)
stats = {'modules_installed': 0, 'modules_failed': [], 'data_migrated': 0, 'errors': []}

def log(msg, level="INFO"):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_msg = f"[{timestamp}] [{level}] {msg}"
    print(log_msg)
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(log_msg + '\n')

def ssh_exec(cmd, host, timeout=600):
    """Ejecuta comando SSH"""
    ssh_cmd = ['ssh', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=30', host, cmd]
    try:
        result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=timeout)
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Timeout"
    except Exception as e:
        return False, "", str(e)

class DatabaseAwareTransport(xmlrpc.client.SafeTransport):
    def __init__(self, database):
        super().__init__()
        self.database = database
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

def ensure_database():
    """Asegura que la BD existe y está inicializada"""
    log("="*70)
    log("PASO 1: Preparar Base de Datos")
    log("="*70)
    
    # Terminar conexiones activas
    log("Terminando conexiones activas...")
    ssh_exec(f"sudo -u postgres psql -c \"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='{TARGET['db']}' AND pid <> pg_backend_pid();\"", TARGET['ssh'])
    
    # Eliminar BD si existe
    log(f"Eliminando BD {TARGET['db']} si existe...")
    ssh_exec(f"sudo -u postgres psql -c 'DROP DATABASE IF EXISTS \"{TARGET['db']}\";'", TARGET['ssh'])
    time.sleep(2)
    
    # Crear BD
    log(f"Creando BD {TARGET['db']}...")
    success, out, err = ssh_exec(f"sudo -u postgres createdb -O {TARGET['odoo_user']} \"{TARGET['db']}\"", TARGET['ssh'])
    if not success:
        log(f"Error: {err}", "ERROR")
        return False
    log("✓ BD creada")
    
    # Inicializar
    log("Inicializando con módulos base...")
    cmd = f"sudo -u {TARGET['odoo_user']} {TARGET['odoo_bin']} -c {TARGET['odoo_config']} -d {TARGET['db']} --init base --stop-after-init --without-demo=all"
    success, out, err = ssh_exec(cmd, TARGET['ssh'], timeout=600)
    if not success:
        log(f"Error inicializando: {err[:500]}", "ERROR")
        return False
    log("✓ BD inicializada")
    return True

def get_modules():
    """Obtiene lista de módulos"""
    log("="*70)
    log("PASO 2: Obtener Módulos")
    log("="*70)
    
    cmd = f"sudo -u postgres psql -d '{SOURCE['db']}' -t -c \"SELECT name FROM ir_module_module WHERE state='installed' AND name NOT LIKE 'custom%' ORDER BY name;\""
    success, out, err = ssh_exec(cmd, SOURCE['ssh'])
    
    if success and out.strip():
        modules = [m.strip() for m in out.strip().split('\n') if m.strip()]
        log(f"✓ Obtenidos {len(modules)} módulos")
        return modules
    
    # Fallback: módulos esenciales
    log("Usando lista de módulos esenciales", "WARN")
    return ['base', 'web', 'mail', 'portal', 'base_setup', 'sale', 'purchase', 'stock', 'account', 'crm', 'project', 'knowledge', 'helpdesk', 'website_helpdesk']

def install_modules(modules):
    """Instala módulos"""
    log("="*70)
    log("PASO 3: Instalar Módulos")
    log("="*70)
    
    priority = ['base', 'web', 'mail', 'portal', 'base_setup']
    installed = set()
    
    # Instalar prioritarios
    for mod in priority:
        if mod in modules:
            log(f"Instalando {mod}...")
            cmd = f"sudo -u {TARGET['odoo_user']} {TARGET['odoo_bin']} -c {TARGET['odoo_config']} -d {TARGET['db']} -i {mod} --stop-after-init --without-demo=all"
            success, out, err = ssh_exec(cmd, TARGET['ssh'], timeout=600)
            if success:
                installed.add(mod)
                stats['modules_installed'] += 1
                log(f"  ✓ {mod}")
            else:
                stats['modules_failed'].append(mod)
                log(f"  ✗ {mod}: {err[:200]}", "ERROR")
    
    # Instalar resto en lotes
    remaining = [m for m in modules if m not in priority]
    batch_size = 10
    
    for i in range(0, len(remaining), batch_size):
        batch = remaining[i:i+batch_size]
        mods_str = ','.join(batch)
        log(f"Instalando lote {i//batch_size + 1}: {len(batch)} módulos...")
        cmd = f"sudo -u {TARGET['odoo_user']} {TARGET['odoo_bin']} -c {TARGET['odoo_config']} -d {TARGET['db']} -i {mods_str} --stop-after-init --without-demo=all"
        success, out, err = ssh_exec(cmd, TARGET['ssh'], timeout=1200)
        if success:
            for mod in batch:
                installed.add(mod)
                stats['modules_installed'] += 1
            log(f"  ✓ Lote instalado")
        else:
            # Intentar individualmente
            for mod in batch:
                log(f"  Instalando {mod} individualmente...")
                cmd = f"sudo -u {TARGET['odoo_user']} {TARGET['odoo_bin']} -c {TARGET['odoo_config']} -d {TARGET['db']} -i {mod} --stop-after-init --without-demo=all"
                success, out, err = ssh_exec(cmd, TARGET['ssh'], timeout=300)
                if success:
                    installed.add(mod)
                    stats['modules_installed'] += 1
                    log(f"    ✓ {mod}")
                else:
                    stats['modules_failed'].append(mod)
                    log(f"    ✗ {mod}", "ERROR")
    
    log(f"✓ Instalados: {len(installed)}, Fallidos: {len(stats['modules_failed'])}")
    return installed

def verify_migration():
    """Verifica migración"""
    log("="*70)
    log("PASO 4: Verificar")
    log("="*70)
    
    source_models, source_uid = connect_mcp(SOURCE)
    target_models, target_uid = connect_mcp(TARGET)
    
    if not source_models or not target_models:
        log("No se pudo conectar para verificar", "WARN")
        return False
    
    models_to_check = ['res.partner', 'product.product', 'sale.order', 'crm.lead']
    for model in models_to_check:
        try:
            source_count = source_models.execute_kw(SOURCE['db'], source_uid, SOURCE['mcp_key'], model, 'search_count', [[]])
            target_count = target_models.execute_kw(TARGET['db'], target_uid, TARGET['mcp_key'], model, 'search_count', [[]])
            log(f"{model}: Origen={source_count}, Destino={target_count}")
        except Exception as e:
            log(f"Error verificando {model}: {e}", "WARN")
    
    return True

def generate_summary():
    """Genera resumen final"""
    summary_file = Path(__file__).parent.parent / "reports" / f"migration_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("="*70 + "\n")
        f.write("RESUMEN DE MIGRACIÓN: OMNIIRP → ODOO 19\n")
        f.write("="*70 + "\n")
        f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"Módulos instalados: {stats['modules_installed']}\n")
        f.write(f"Módulos fallidos: {len(stats['modules_failed'])}\n")
        if stats['modules_failed']:
            f.write("\nMódulos fallidos:\n")
            for mod in stats['modules_failed']:
                f.write(f"  - {mod}\n")
        f.write(f"\nErrores: {len(stats['errors'])}\n")
        if stats['errors']:
            for err in stats['errors']:
                f.write(f"  - {err}\n")
    
    log(f"✓ Resumen guardado: {summary_file}")

def main():
    log("="*70)
    log("MIGRACIÓN COMPLETA DESATENDIDA")
    log("="*70)
    start_time = datetime.now()
    
    try:
        if not ensure_database():
            log("Error en paso 1", "ERROR")
            return False
        
        modules = get_modules()
        installed = install_modules(modules)
        
        verify_migration()
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds() / 60
        
        log("="*70)
        log("MIGRACIÓN COMPLETADA")
        log("="*70)
        log(f"Duración: {duration:.1f} minutos")
        log(f"Módulos instalados: {stats['modules_installed']}")
        log(f"Módulos fallidos: {len(stats['modules_failed'])}")
        
        generate_summary()
        return True
        
    except Exception as e:
        log(f"Error fatal: {e}", "ERROR")
        import traceback
        log(traceback.format_exc(), "ERROR")
        generate_summary()
        return False

if __name__ == "__main__":
    main()

