#!/usr/bin/env python3
"""
Instalación de Módulos en Lotes
Ubicado en: prompts/install_modules_batch.py
"""

import subprocess
import time
from datetime import datetime
from pathlib import Path

TARGET = {
    'ssh': 'diego.avalos@laia.one',
    'db': 'omnierp_migrated',
    'odoo_bin': '/opt/odoo19/venv/bin/python3 /opt/odoo19/odoo-bin',
    'odoo_config': '/etc/odoo19.conf',
    'odoo_user': 'odoo19'
}

log_file = Path(__file__).parent.parent / "reports" / f"modules_installation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
log_file.parent.mkdir(exist_ok=True)

def log(msg, level="INFO"):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_msg = f"[{timestamp}] [{level}] {msg}"
    print(log_msg)
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(log_msg + '\n')

def ssh_exec(cmd, timeout=600):
    ssh_cmd = ['ssh', '-o', 'StrictHostKeyChecking=no', TARGET['ssh'], cmd]
    try:
        result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=timeout)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def install_module(module_name):
    """Instala un módulo"""
    cmd = f"sudo -u {TARGET['odoo_user']} bash -c 'cd /opt/odoo19 && source venv/bin/activate && python3 odoo-bin -c {TARGET['odoo_config']} -d {TARGET['db']} -i {module_name} --stop-after-init --without-demo=all'"
    success, out, err = ssh_exec(cmd, timeout=600)
    return success

# Leer módulos
with open('/tmp/modules_to_install.txt', 'r') as f:
    all_modules = [l.strip() for l in f if l.strip()]

# Prioridad
priority = ['base', 'web', 'mail', 'portal', 'base_setup', 'sale', 'purchase', 'stock', 'account', 'crm', 'project', 'knowledge', 'helpdesk', 'website_helpdesk']

log(f"Total módulos: {len(all_modules)}")

# Instalar prioritarios
for mod in priority:
    if mod in all_modules:
        log(f"Instalando {mod}...")
        if install_module(mod):
            log(f"  ✓ {mod}")
        else:
            log(f"  ✗ {mod}", "ERROR")

# Instalar resto en lotes pequeños
remaining = [m for m in all_modules if m not in priority]
batch_size = 5

for i in range(0, len(remaining), batch_size):
    batch = remaining[i:i+batch_size]
    log(f"Lote {i//batch_size + 1}: {', '.join(batch)}")
    for mod in batch:
        if install_module(mod):
            log(f"  ✓ {mod}")
        else:
            log(f"  ✗ {mod}", "ERROR")
    time.sleep(5)  # Pausa entre lotes

log("Instalación completada")

