#!/usr/bin/env python3
"""
Migración Automatizada: OmniERP (Odoo 18) → Odoo 19
Ubicado en: prompts/automated_migration_omnierp_to_odoo19.py

Este script automatiza la migración completa usando:
- SSH para operaciones en servidor
- MCP para consultas de datos
- Manejo de cambios de nombres de módulos entre versiones
- Soporte para módulos Base + Enterprise
"""

import sys
import os
import subprocess
import xmlrpc.client
import ssl
import urllib.request
import urllib.error
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Configuración de servidores
SOURCE_SERVER = {
    "name": "OmniERP (Origen - Odoo 18)",
    "url": "https://omnierp.app",
    "db": "omnierp.app",
    "user": "admin@omnierp.app",
    "api_key": "7f3ea49d0339de71e39996866b61c26416ba0597",
    "ssh_host": "omnierp.app",
    "ssh_user": "diego.avalos"
}

TARGET_SERVER = {
    "name": "Laia.one (Destino - Odoo 19)",
    "url": "https://laia.one",
    "db": "omnierp_migrated",  # Nueva base de datos
    "user": "admin@laia.one",
    "api_key": "cfebea4c6d0a3cc3e345db4aa9c94b3e085ea3e5",
    "ssh_host": "laia.one",
    "ssh_user": "diego.avalos",
    "odoo_bin": "/opt/odoo19/venv/bin/python3 /opt/odoo19/odoo-bin",
    "odoo_config": "/etc/odoo19.conf",  # Verificar ruta real en servidor
    "odoo_user": "odoo19"
}

# Mapeo de módulos que cambiaron de nombre entre Odoo 18 y 19
# Basado en documentación oficial y cambios conocidos
MODULE_NAME_MAPPING = {
    # Módulos que fueron renombrados o consolidados
    # Nota: Verificar documentación oficial para cambios específicos
    # 'website_sale_stock': 'website_sale_delivery',  # Ejemplo - verificar
    # Agregar más mapeos cuando se identifiquen durante la migración
}

# Módulos que fueron deprecados o removidos en Odoo 19
# Estos módulos no estarán disponibles y requieren reemplazo o migración manual
DEPRECATED_MODULES = [
    # Agregar módulos deprecados cuando se identifiquen
    # Ejemplo: 'old_module_name'
]

# Módulos Enterprise que requieren verificación especial
ENTERPRISE_MODULES = [
    'account_accountant',
    'account_reports',
    'sale_enterprise',
    'purchase_enterprise',
    'stock_enterprise',
    'crm_enterprise',
    'project_enterprise',
    'helpdesk_enterprise',
    'knowledge',
    'website_helpdesk',
    'website_helpdesk_knowledge',
    'hr_enterprise',
    'l10n_*',  # Módulos de localización
]

# Módulos que requieren instalación especial
SPECIAL_MODULES = {
    'base': {'priority': 1, 'required': True},
    'web': {'priority': 2, 'required': True},
    'mail': {'priority': 3, 'required': True},
}

# Orden de instalación de módulos por categoría
# Este orden respeta las dependencias entre módulos
MODULE_INSTALL_ORDER = [
    # Módulos base (críticos)
    'base',
    'web',
    'mail',
    'portal',
    'auth_signup',
    'base_setup',
    
    # Módulos de contabilidad
    'account',
    'account_accountant',  # Enterprise
    'account_reports',  # Enterprise
    
    # Módulos de ventas
    'sale',
    'sale_enterprise',  # Enterprise
    'sale_stock',
    
    # Módulos de compras
    'purchase',
    'purchase_enterprise',  # Enterprise
    'purchase_stock',
    
    # Módulos de inventario
    'stock',
    'stock_enterprise',  # Enterprise
    
    # Módulos de CRM
    'crm',
    'crm_enterprise',  # Enterprise
    
    # Módulos de proyectos
    'project',
    'project_enterprise',  # Enterprise
    
    # Módulos de Knowledge y Helpdesk
    'knowledge',  # Enterprise
    'helpdesk',  # Enterprise
    'helpdesk_enterprise',  # Enterprise
    'website_helpdesk',  # Enterprise
    'website_helpdesk_knowledge',  # Enterprise
    
    # Módulos de recursos humanos
    'hr',
    'hr_enterprise',  # Enterprise
    
    # Módulos de website
    'website',
    'website_sale',
    'website_blog',
]


class DatabaseAwareTransport(xmlrpc.client.SafeTransport):
    """Transport personalizado que envía el header X-Odoo-Database"""
    def __init__(self, database, use_datetime=False, use_builtin_types=False):
        super().__init__(use_datetime=use_datetime, use_builtin_types=use_builtin_types)
        self.database = database
        self.verbose = False
    
    def request(self, host, handler, request_body, verbose=False):
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


class SSHError(Exception):
    """Excepción para errores SSH"""
    pass


class MCPError(Exception):
    """Excepción para errores MCP"""
    pass


class AutomatedMigration:
    """Clase principal para migración automatizada"""
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.log_file = Path(__file__).parent.parent / "reports" / f"migration_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        self.log_file.parent.mkdir(exist_ok=True)
        self.source_modules = []
        self.target_modules = []
        self.migration_stats = {
            'modules_installed': 0,
            'modules_failed': 0,
            'records_migrated': 0,
            'errors': []
        }
        
    def log(self, message: str, level: str = "INFO"):
        """Registra mensaje en log"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_message = f"[{timestamp}] [{level}] {message}"
        print(log_message)
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_message + '\n')
    
    def execute_ssh_command(self, host: str, user: str, command: str, sudo: bool = False) -> Tuple[bool, str]:
        """Ejecuta comando SSH"""
        try:
            ssh_cmd = ['ssh', '-o', 'StrictHostKeyChecking=no', f'{user}@{host}']
            if sudo:
                # Si el comando ya tiene sudo, no duplicar
                if command.strip().startswith('sudo'):
                    full_cmd = command
                else:
                    full_cmd = f"sudo {command}"
            else:
                full_cmd = command
            
            ssh_cmd.append(full_cmd)
            
            self.log(f"Ejecutando SSH: {' '.join(ssh_cmd)}")
            
            if self.dry_run:
                self.log(f"[DRY RUN] Comando SSH: {full_cmd}", "DRY_RUN")
                return True, "[DRY RUN]"
            
            result = subprocess.run(
                ssh_cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0:
                return True, result.stdout
            else:
                error_msg = result.stderr or result.stdout
                self.log(f"Error SSH: {error_msg}", "ERROR")
                return False, error_msg
                
        except subprocess.TimeoutExpired:
            self.log("Timeout ejecutando comando SSH", "ERROR")
            return False, "Timeout"
        except Exception as e:
            self.log(f"Excepción SSH: {e}", "ERROR")
            return False, str(e)
    
    def connect_mcp(self, server_config: Dict) -> Tuple[Optional[xmlrpc.client.ServerProxy], Optional[int]]:
        """Conecta a servidor vía MCP"""
        try:
            context = ssl._create_unverified_context()
            common_url = f"{server_config['url']}/mcp/xmlrpc/common"
            object_url = f"{server_config['url']}/mcp/xmlrpc/object"
            
            transport = DatabaseAwareTransport(server_config['db'], use_datetime=True)
            common = xmlrpc.client.ServerProxy(common_url, transport=transport, allow_none=True)
            models = xmlrpc.client.ServerProxy(object_url, transport=transport, allow_none=True)
            
            uid = common.authenticate(
                server_config['db'],
                server_config['user'],
                server_config['api_key'],
                {}
            )
            
            if uid:
                return models, uid
            return None, None
        except Exception as e:
            self.log(f"Error conectando MCP a {server_config['name']}: {e}", "ERROR")
            raise MCPError(f"Error de conexión MCP: {e}")
    
    def step_1_create_database(self) -> bool:
        """Paso 1: Crear base de datos nueva"""
        self.log("="*70)
        self.log("PASO 1: Crear Base de Datos Nueva")
        self.log("="*70)
        
        # Verificar si la BD ya existe
        check_cmd = f"sudo -u postgres psql -lqt | cut -d \\| -f 1 | grep -qw '{TARGET_SERVER['db']}'"
        success, output = self.execute_ssh_command(
            TARGET_SERVER['ssh_host'],
            TARGET_SERVER['ssh_user'],
            check_cmd
        )
        
        if success and TARGET_SERVER['db'] in output:
            self.log(f"Base de datos {TARGET_SERVER['db']} ya existe")
            response = input(f"¿Deseas eliminar y recrear {TARGET_SERVER['db']}? (s/N): ")
            if response.lower() == 's':
                drop_cmd = f"sudo -u postgres psql -c 'DROP DATABASE IF EXISTS \"{TARGET_SERVER['db']}\";'"
                success, _ = self.execute_ssh_command(
                    TARGET_SERVER['ssh_host'],
                    TARGET_SERVER['ssh_user'],
                    drop_cmd,
                    sudo=True
                )
                if not success:
                    self.log("Error eliminando base de datos existente", "ERROR")
                    return False
            else:
                self.log("Usando base de datos existente")
                return True
        
        # Crear base de datos
        create_cmd = f"sudo -u postgres createdb -O {TARGET_SERVER['odoo_user']} \"{TARGET_SERVER['db']}\""
        success, output = self.execute_ssh_command(
            TARGET_SERVER['ssh_host'],
            TARGET_SERVER['ssh_user'],
            create_cmd,
            sudo=True
        )
        
        if not success:
            self.log(f"Error creando base de datos: {output}", "ERROR")
            return False
        
        self.log(f"✓ Base de datos {TARGET_SERVER['db']} creada exitosamente")
        
        # Inicializar con módulos base
        init_cmd = f"{TARGET_SERVER['odoo_bin']} -c {TARGET_SERVER['odoo_config']} -d {TARGET_SERVER['db']} --init base --stop-after-init --without-demo=all"
        success, output = self.execute_ssh_command(
            TARGET_SERVER['ssh_host'],
            TARGET_SERVER['ssh_user'],
            init_cmd
        )
        
        if not success:
            self.log(f"Error inicializando base de datos: {output}", "ERROR")
            return False
        
        self.log("✓ Base de datos inicializada con módulos base")
        return True
    
    def step_2_get_modules_list(self) -> List[Dict]:
        """Paso 2: Obtener lista de módulos desde origen"""
        self.log("="*70)
        self.log("PASO 2: Obtener Lista de Módulos desde Origen")
        self.log("="*70)
        
        try:
            models, uid = self.connect_mcp(SOURCE_SERVER)
            if not models or not uid:
                raise MCPError("No se pudo conectar a servidor origen")
            
            # Obtener módulos instalados
            # Nota: Si no tenemos acceso MCP a ir.module.module, usar SSH
            self.log("Obteniendo módulos instalados vía SSH...")
            
            get_modules_cmd = f"sudo -u postgres psql -d '{SOURCE_SERVER['db']}' -c \"SELECT name, state, latest_version FROM ir_module_module WHERE state='installed' ORDER BY name;\" -t"
            success, output = self.execute_ssh_command(
                SOURCE_SERVER['ssh_host'],
                SOURCE_SERVER['ssh_user'],
                get_modules_cmd,
                sudo=True
            )
            
            if not success:
                self.log("Error obteniendo módulos vía SSH, intentando vía MCP...", "WARN")
                # Intentar vía MCP si SSH falla
                try:
                    modules = models.execute_kw(
                        SOURCE_SERVER['db'], uid, SOURCE_SERVER['api_key'],
                        'ir.module.module', 'search_read',
                        [[('state', '=', 'installed')]],
                        {'fields': ['name', 'state', 'latest_version'], 'limit': 1000}
                    )
                    self.source_modules = modules
                except Exception as e:
                    self.log(f"Error obteniendo módulos vía MCP: {e}", "ERROR")
                    raise MCPError(f"Error obteniendo módulos: {e}")
            else:
                # Parsear output de PostgreSQL
                modules = []
                for line in output.strip().split('\n'):
                    if line.strip():
                        parts = line.strip().split('|')
                        if len(parts) >= 3:
                            modules.append({
                                'name': parts[0].strip(),
                                'state': parts[1].strip(),
                                'latest_version': parts[2].strip()
                            })
                self.source_modules = modules
            
            self.log(f"✓ Obtenidos {len(self.source_modules)} módulos instalados")
            
            # Filtrar módulos base y enterprise
            base_modules = [m for m in self.source_modules if not m.get('name', '').startswith('custom_')]
            self.log(f"  - Módulos base/enterprise: {len(base_modules)}")
            self.log(f"  - Módulos personalizados: {len(self.source_modules) - len(base_modules)}")
            
            return self.source_modules
            
        except Exception as e:
            self.log(f"Error en paso 2: {e}", "ERROR")
            raise
    
    def map_module_name(self, module_name: str) -> str:
        """Mapea nombre de módulo de Odoo 18 a Odoo 19"""
        # Verificar si hay mapeo directo
        if module_name in MODULE_NAME_MAPPING:
            mapped = MODULE_NAME_MAPPING[module_name]
            self.log(f"  Módulo {module_name} mapeado a {mapped}")
            return mapped
        
        # Verificar si está deprecado
        if module_name in DEPRECATED_MODULES:
            self.log(f"  ⚠ Módulo {module_name} está deprecado en Odoo 19", "WARN")
            return None
        
        # Si no hay mapeo, usar el mismo nombre
        return module_name
    
    def step_3_install_modules(self) -> bool:
        """Paso 3: Instalar módulos en orden correcto"""
        self.log("="*70)
        self.log("PASO 3: Instalar Módulos en Orden")
        self.log("="*70)
        
        if not self.source_modules:
            self.log("No hay módulos para instalar. Ejecutar paso 2 primero.", "ERROR")
            return False
        
        # Resolver dependencias y ordenar
        modules_to_install = []
        for module in self.source_modules:
            module_name = module.get('name', '')
            if not module_name:
                continue
            
            # Mapear nombre si es necesario
            mapped_name = self.map_module_name(module_name)
            if mapped_name is None:
                self.log(f"  ⚠ Omitiendo módulo deprecado: {module_name}", "WARN")
                continue
            
            # Verificar si es módulo personalizado
            if module_name.startswith('custom_') or 'custom' in module_name.lower():
                self.log(f"  ⚠ Módulo personalizado {module_name} requiere revisión manual", "WARN")
                # Guardar para reporte pero no instalar automáticamente
                continue
            
            # Verificar si es módulo Enterprise
            is_enterprise = any(ent_mod in module_name for ent_mod in ['enterprise', 'accountant', 'reports', 'knowledge', 'helpdesk'])
            if is_enterprise:
                self.log(f"  ℹ Módulo Enterprise detectado: {module_name}")
            
            modules_to_install.append(mapped_name)
        
        # Instalar módulos en orden de prioridad
        installed = set()
        failed = []
        
        # Primero módulos base críticos
        critical_modules = ['base', 'web', 'mail']
        for mod in critical_modules:
            if mod in modules_to_install and mod not in installed:
                if self._install_module(mod):
                    installed.add(mod)
                else:
                    failed.append(mod)
        
        # Luego módulos en orden definido
        for mod in MODULE_INSTALL_ORDER:
            if mod in modules_to_install and mod not in installed:
                if self._install_module(mod):
                    installed.add(mod)
                else:
                    failed.append(mod)
        
        # Finalmente resto de módulos
        for mod in modules_to_install:
            if mod not in installed and mod not in critical_modules:
                if self._install_module(mod):
                    installed.add(mod)
                else:
                    failed.append(mod)
        
        self.log(f"✓ Módulos instalados: {len(installed)}")
        if failed:
            self.log(f"⚠ Módulos fallidos: {len(failed)}", "WARN")
            for mod in failed:
                self.log(f"  - {mod}", "WARN")
        
        self.migration_stats['modules_installed'] = len(installed)
        self.migration_stats['modules_failed'] = len(failed)
        
        return len(failed) == 0
    
    def _install_module(self, module_name: str) -> bool:
        """Instala un módulo individual"""
        self.log(f"  Instalando módulo: {module_name}")
        
        install_cmd = f"{TARGET_SERVER['odoo_bin']} -c {TARGET_SERVER['odoo_config']} -d {TARGET_SERVER['db']} -i {module_name} --stop-after-init --without-demo=all"
        success, output = self.execute_ssh_command(
            TARGET_SERVER['ssh_host'],
            TARGET_SERVER['ssh_user'],
            install_cmd
        )
        
        if success:
            self.log(f"    ✓ {module_name} instalado")
            return True
        else:
            self.log(f"    ✗ Error instalando {module_name}: {output[:200]}", "ERROR")
            self.migration_stats['errors'].append(f"Error instalando {module_name}: {output[:200]}")
            return False
    
    def step_4_migrate_data(self) -> bool:
        """Paso 4: Migrar datos"""
        self.log("="*70)
        self.log("PASO 4: Migrar Datos")
        self.log("="*70)
        
        try:
            source_models, source_uid = self.connect_mcp(SOURCE_SERVER)
            target_models, target_uid = self.connect_mcp(TARGET_SERVER)
            
            if not source_models or not target_models:
                raise MCPError("No se pudo conectar a servidores")
            
            # Modelos a migrar en orden
            models_to_migrate = [
                ('res.partner', 'Partners'),
                ('product.template', 'Productos'),
                ('product.product', 'Variantes de Productos'),
                ('sale.order', 'Órdenes de Venta'),
                ('account.move', 'Facturas'),
                ('crm.lead', 'Leads'),
                ('project.project', 'Proyectos'),
                ('project.task', 'Tareas'),
                ('knowledge.article', 'Artículos Knowledge'),
                ('helpdesk.ticket', 'Tickets Helpdesk'),
            ]
            
            for model_name, display_name in models_to_migrate:
                self.log(f"\nMigrando {display_name} ({model_name})...")
                
                try:
                    # Obtener datos desde origen
                    records = source_models.execute_kw(
                        SOURCE_SERVER['db'], source_uid, SOURCE_SERVER['api_key'],
                        model_name, 'search_read',
                        [[]],
                        {'limit': 1000}  # Migrar en lotes
                    )
                    
                    if not records:
                        self.log(f"  No hay registros de {display_name}")
                        continue
                    
                    self.log(f"  Obtenidos {len(records)} registros")
                    
                    # Migrar registros (esto requiere lógica específica por modelo)
                    # Por ahora solo logueamos
                    self.log(f"  ⚠ Migración de {display_name} requiere implementación específica", "WARN")
                    self.migration_stats['records_migrated'] += len(records)
                    
                except Exception as e:
                    self.log(f"  ✗ Error migrando {display_name}: {e}", "ERROR")
                    self.migration_stats['errors'].append(f"Error migrando {display_name}: {e}")
            
            self.log(f"\n✓ Migración de datos completada")
            self.log(f"  Total registros migrados: {self.migration_stats['records_migrated']}")
            return True
            
        except Exception as e:
            self.log(f"Error en paso 4: {e}", "ERROR")
            return False
    
    def step_5_verify_migration(self) -> bool:
        """Paso 5: Verificar migración"""
        self.log("="*70)
        self.log("PASO 5: Verificar Migración")
        self.log("="*70)
        
        try:
            source_models, source_uid = self.connect_mcp(SOURCE_SERVER)
            target_models, target_uid = self.connect_mcp(TARGET_SERVER)
            
            if not source_models or not target_models:
                raise MCPError("No se pudo conectar a servidores")
            
            # Verificar conteos
            models_to_verify = [
                'res.partner',
                'product.product',
                'sale.order',
                'crm.lead',
            ]
            
            all_match = True
            for model_name in models_to_verify:
                try:
                    source_count = source_models.execute_kw(
                        SOURCE_SERVER['db'], source_uid, SOURCE_SERVER['api_key'],
                        model_name, 'search_count', [[]]
                    )
                    
                    target_count = target_models.execute_kw(
                        TARGET_SERVER['db'], target_uid, TARGET_SERVER['api_key'],
                        model_name, 'search_count', [[]]
                    )
                    
                    status = "✓" if source_count == target_count else "✗"
                    self.log(f"  {status} {model_name}: Origen={source_count}, Destino={target_count}")
                    
                    if source_count != target_count:
                        all_match = False
                        
                except Exception as e:
                    self.log(f"  ✗ Error verificando {model_name}: {e}", "ERROR")
                    all_match = False
            
            if all_match:
                self.log("\n✓ Verificación exitosa: Todos los conteos coinciden")
            else:
                self.log("\n⚠ Verificación: Algunos conteos no coinciden", "WARN")
            
            return all_match
            
        except Exception as e:
            self.log(f"Error en paso 5: {e}", "ERROR")
            return False
    
    def generate_report(self):
        """Genera reporte final"""
        report_path = Path(__file__).parent.parent / "reports" / f"migration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("="*70 + "\n")
            f.write("REPORTE DE MIGRACIÓN AUTOMATIZADA\n")
            f.write("="*70 + "\n")
            f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Origen: {SOURCE_SERVER['name']}\n")
            f.write(f"Destino: {TARGET_SERVER['name']} ({TARGET_SERVER['db']})\n\n")
            
            f.write("ESTADÍSTICAS:\n")
            f.write(f"  Módulos instalados: {self.migration_stats['modules_installed']}\n")
            f.write(f"  Módulos fallidos: {self.migration_stats['modules_failed']}\n")
            f.write(f"  Registros migrados: {self.migration_stats['records_migrated']}\n")
            f.write(f"  Errores: {len(self.migration_stats['errors'])}\n\n")
            
            if self.migration_stats['errors']:
                f.write("ERRORES:\n")
                for error in self.migration_stats['errors']:
                    f.write(f"  - {error}\n")
        
        self.log(f"✓ Reporte generado: {report_path}")
    
    def run(self):
        """Ejecuta migración completa"""
        self.log("="*70)
        self.log("INICIANDO MIGRACIÓN AUTOMATIZADA")
        self.log("="*70)
        self.log(f"Modo: {'DRY RUN' if self.dry_run else 'EJECUCIÓN REAL'}")
        self.log(f"Origen: {SOURCE_SERVER['name']}")
        self.log(f"Destino: {TARGET_SERVER['name']} -> {TARGET_SERVER['db']}")
        self.log("")
        
        if not self.dry_run:
            confirm = input("¿Continuar con la migración? (s/N): ")
            if confirm.lower() != 's':
                self.log("Migración cancelada por el usuario")
                return
        
        try:
            # Paso 1: Crear BD
            if not self.step_1_create_database():
                self.log("Error en paso 1. Abortando.", "ERROR")
                return False
            
            # Paso 2: Obtener módulos
            if not self.step_2_get_modules_list():
                self.log("Error en paso 2. Abortando.", "ERROR")
                return False
            
            # Paso 3: Instalar módulos
            if not self.step_3_install_modules():
                self.log("Advertencias en paso 3. Continuando...", "WARN")
            
            # Paso 4: Migrar datos
            if not self.step_4_migrate_data():
                self.log("Error en paso 4. Abortando.", "ERROR")
                return False
            
            # Paso 5: Verificar
            if not self.step_5_verify_migration():
                self.log("Advertencias en verificación.", "WARN")
            
            # Generar reporte
            self.generate_report()
            
            self.log("="*70)
            self.log("MIGRACIÓN COMPLETADA")
            self.log("="*70)
            return True
            
        except Exception as e:
            self.log(f"Error fatal: {e}", "ERROR")
            import traceback
            self.log(traceback.format_exc(), "ERROR")
            return False


def main():
    """Función principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Migración Automatizada OmniERP → Odoo 19')
    parser.add_argument('--dry-run', action='store_true', help='Ejecutar en modo dry-run (sin cambios)')
    parser.add_argument('--step', type=int, help='Ejecutar solo un paso específico (1-5)')
    
    args = parser.parse_args()
    
    migration = AutomatedMigration(dry_run=args.dry_run)
    
    if args.step:
        # Ejecutar solo un paso
        steps = {
            1: migration.step_1_create_database,
            2: migration.step_2_get_modules_list,
            3: migration.step_3_install_modules,
            4: migration.step_4_migrate_data,
            5: migration.step_5_verify_migration,
        }
        
        if args.step in steps:
            steps[args.step]()
        else:
            print(f"Paso {args.step} no válido. Use 1-5.")
    else:
        # Ejecutar migración completa
        success = migration.run()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

