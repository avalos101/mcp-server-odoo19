#!/usr/bin/env python3
"""
Análisis y Plan de Migración: OmniERP (Odoo 18) → Odoo 19
Ubicado en: prompts/analyze_migration_omnierp_to_odoo19.py

Este script analiza ambos servidores y genera un plan detallado de migración
sin ejecutar ninguna acción de migración.
"""

import xmlrpc.client
import ssl
import urllib.request
import urllib.error
import json
from datetime import datetime
from pathlib import Path

# Configuración de servidores
SOURCE_SERVER = {
    "name": "OmniERP (Origen - Odoo 18)",
    "url": "https://omnierp.app",
    "db": "omnierp.app",
    "user": "admin@omnierp.app",
    "api_key": "7f3ea49d0339de71e39996866b61c26416ba0597"
}

TARGET_SERVER = {
    "name": "Laia.one (Destino - Odoo 19)",
    "url": "https://laia.one",
    "db": "admin-laia",
    "user": "admin@laia.one",
    "api_key": "cfebea4c6d0a3cc3e345db4aa9c94b3e085ea3e5"
}


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


class MigrationAnalyzer:
    """Analizador de migración"""
    
    def __init__(self):
        self.source_info = {}
        self.target_info = {}
        self.analysis_results = {}
        
    def connect_to_server(self, server_config):
        """Conecta a un servidor y retorna conexión"""
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
            print(f"✗ Error conectando a {server_config['name']}: {e}")
            return None, None
    
    def analyze_installed_modules(self, models, uid, server_config):
        """Analiza módulos instalados"""
        print(f"\n  Analizando módulos instalados...")
        modules_info = {
            'total': 0,
            'custom': [],
            'standard': [],
            'by_category': {}
        }
        
        try:
            # Obtener todos los módulos instalados
            modules = models.execute_kw(
                server_config['db'], uid, server_config['api_key'],
                'ir.module.module', 'search_read',
                [[('state', '=', 'installed')]],
                {'fields': ['name', 'category_id', 'author', 'summary', 'latest_version'], 'limit': 1000}
            )
            
            modules_info['total'] = len(modules)
            
            for module in modules:
                category = module.get('category_id', [False, ''])[1] if module.get('category_id') else 'Sin categoría'
                author = module.get('author', '')
                
                module_data = {
                    'name': module.get('name', ''),
                    'category': category,
                    'author': author,
                    'version': module.get('latest_version', 'N/A'),
                    'summary': module.get('summary', '')
                }
                
                if 'custom' in author.lower() or 'custom' in module.get('name', '').lower():
                    modules_info['custom'].append(module_data)
                else:
                    modules_info['standard'].append(module_data)
                
                if category not in modules_info['by_category']:
                    modules_info['by_category'][category] = []
                modules_info['by_category'][category].append(module_data['name'])
            
            print(f"    ✓ {modules_info['total']} módulos instalados")
            print(f"    ✓ {len(modules_info['custom'])} módulos personalizados")
            print(f"    ✓ {len(modules_info['standard'])} módulos estándar")
            
        except Exception as e:
            print(f"    ⚠ Error analizando módulos: {e}")
        
        return modules_info
    
    def analyze_data_volumes(self, models, uid, server_config):
        """Analiza volúmenes de datos"""
        print(f"\n  Analizando volúmenes de datos...")
        data_volumes = {}
        
        # Modelos clave a analizar
        key_models = [
            'res.partner',
            'product.product',
            'product.template',
            'sale.order',
            'purchase.order',
            'account.move',
            'account.move.line',
            'stock.picking',
            'crm.lead',
            'project.project',
            'project.task',
            'hr.employee',
            'mail.message',
            'ir.attachment',
        ]
        
        for model_name in key_models:
            try:
                count = models.execute_kw(
                    server_config['db'], uid, server_config['api_key'],
                    model_name, 'search_count', [[]]
                )
                data_volumes[model_name] = count
            except:
                data_volumes[model_name] = "N/A"
        
        total_records = sum(v for v in data_volumes.values() if isinstance(v, int))
        print(f"    ✓ Total aproximado de registros: {total_records:,}")
        
        return data_volumes
    
    def analyze_customizations(self, models, uid, server_config):
        """Analiza personalizaciones"""
        print(f"\n  Analizando personalizaciones...")
        customizations = {
            'custom_models': [],
            'custom_views': 0,
            'custom_reports': 0,
            'workflows': 0,
            'automated_actions': 0
        }
        
        try:
            # Modelos personalizados
            custom_models = models.execute_kw(
                server_config['db'], uid, server_config['api_key'],
                'ir.model', 'search_read',
                [[('custom', '=', True)]],
                {'fields': ['model', 'name'], 'limit': 100}
            )
            customizations['custom_models'] = [m.get('model', '') for m in custom_models]
            print(f"    ✓ {len(customizations['custom_models'])} modelos personalizados")
            
            # Vistas personalizadas
            try:
                custom_views = models.execute_kw(
                    server_config['db'], uid, server_config['api_key'],
                    'ir.ui.view', 'search_count',
                    [[('custom', '=', True)]]
                )
                customizations['custom_views'] = custom_views
                print(f"    ✓ {custom_views} vistas personalizadas")
            except:
                pass
            
        except Exception as e:
            print(f"    ⚠ Error analizando personalizaciones: {e}")
        
        return customizations
    
    def analyze_server(self, server_config):
        """Analiza un servidor completo"""
        print(f"\n{'='*70}")
        print(f"ANALIZANDO: {server_config['name']}")
        print(f"{'='*70}")
        
        models, uid = self.connect_to_server(server_config)
        
        if not models or not uid:
            print(f"✗ No se pudo conectar a {server_config['name']}")
            return None
        
        print(f"✓ Conexión establecida (UID: {uid})")
        
        server_info = {
            'name': server_config['name'],
            'url': server_config['url'],
            'db': server_config['db'],
            'uid': uid,
            'modules': {},
            'data_volumes': {},
            'customizations': {}
        }
        
        # Analizar módulos
        server_info['modules'] = self.analyze_installed_modules(models, uid, server_config)
        
        # Analizar volúmenes de datos
        server_info['data_volumes'] = self.analyze_data_volumes(models, uid, server_config)
        
        # Analizar personalizaciones
        server_info['customizations'] = self.analyze_customizations(models, uid, server_config)
        
        return server_info
    
    def compare_servers(self):
        """Compara servidor origen y destino"""
        print(f"\n{'='*70}")
        print("COMPARACIÓN DE SERVIDORES")
        print(f"{'='*70}")
        
        comparison = {
            'modules_missing_in_target': [],
            'modules_to_install': [],
            'data_differences': {},
            'compatibility_issues': []
        }
        
        # Comparar módulos
        source_modules = set(m['name'] for m in self.source_info['modules']['standard'] + self.source_info['modules']['custom'])
        target_modules = set(m['name'] for m in self.target_info['modules']['standard'] + self.target_info['modules']['custom'])
        
        missing_modules = source_modules - target_modules
        comparison['modules_missing_in_target'] = list(missing_modules)
        
        print(f"\nMódulos en origen que no están en destino: {len(missing_modules)}")
        if missing_modules:
            print("  Módulos faltantes:")
            for mod in sorted(list(missing_modules)[:20]):  # Mostrar primeros 20
                print(f"    - {mod}")
            if len(missing_modules) > 20:
                print(f"    ... y {len(missing_modules) - 20} más")
        
        # Comparar volúmenes de datos
        for model, source_count in self.source_info['data_volumes'].items():
            target_count = self.target_info['data_volumes'].get(model, 0)
            if isinstance(source_count, int) and isinstance(target_count, int):
                if source_count > 0:
                    comparison['data_differences'][model] = {
                        'source': source_count,
                        'target': target_count,
                        'difference': source_count - target_count
                    }
        
        return comparison
    
    def generate_migration_plan(self, comparison):
        """Genera plan de migración"""
        print(f"\n{'='*70}")
        print("GENERANDO PLAN DE MIGRACIÓN")
        print(f"{'='*70}")
        
        plan = {
            'pre_migration': [],
            'migration_steps': [],
            'post_migration': [],
            'risks': [],
            'estimated_time': 'N/A'
        }
        
        # Pre-migración
        plan['pre_migration'] = [
            "1. Crear backup completo de la base de datos origen (OmniERP)",
            "2. Verificar espacio en disco en servidor destino (mínimo 2x tamaño de BD origen)",
            "3. Verificar que todos los módulos necesarios estén disponibles para Odoo 19",
            "4. Crear base de datos nueva en servidor destino o preparar base existente",
            "5. Documentar configuraciones personalizadas (vistas, workflows, etc.)",
            "6. Verificar compatibilidad de módulos personalizados con Odoo 19",
            "7. Preparar scripts de migración de datos personalizados si es necesario"
        ]
        
        # Pasos de migración
        plan['migration_steps'] = [
            "1. Instalar módulos base en servidor destino",
            "2. Instalar módulos estándar necesarios (verificar compatibilidad Odoo 19)",
            "3. Migrar datos maestros (partners, productos, etc.)",
            "4. Migrar datos transaccionales (ventas, compras, facturas, etc.)",
            "5. Migrar documentos adjuntos",
            "6. Migrar mensajes y comunicaciones",
            "7. Aplicar personalizaciones (vistas, reportes, workflows)",
            "8. Configurar usuarios y permisos",
            "9. Verificar integridad de datos",
            "10. Realizar pruebas de funcionalidad"
        ]
        
        # Post-migración
        plan['post_migration'] = [
            "1. Verificar acceso de usuarios",
            "2. Probar funcionalidades críticas",
            "3. Verificar reportes y vistas personalizadas",
            "4. Configurar backups automáticos",
            "5. Documentar cambios y configuraciones",
            "6. Capacitar usuarios en nuevas funcionalidades de Odoo 19",
            "7. Monitorear sistema durante período de transición"
        ]
        
        # Riesgos identificados
        plan['risks'] = [
            f"Migración de {len(comparison['modules_missing_in_target'])} módulos que no están en destino",
            "Posibles incompatibilidades entre Odoo 18 y Odoo 19",
            "Volumen grande de datos a migrar (verificar tiempos)",
            "Personalizaciones que requieren adaptación",
            "Posible downtime durante migración"
        ]
        
        # Estimar tiempo
        total_records = sum(v for v in self.source_info['data_volumes'].values() if isinstance(v, int))
        if total_records > 0:
            estimated_hours = max(2, total_records / 10000)  # Estimación aproximada
            plan['estimated_time'] = f"Aproximadamente {estimated_hours:.1f} horas (depende de volumen y complejidad)"
        
        return plan
    
    def generate_report(self, comparison, plan):
        """Genera reporte completo"""
        report_path = Path(__file__).parent.parent / "reports" / f"migration_plan_omnierp_to_odoo19_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        report_path.parent.mkdir(exist_ok=True)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("="*70 + "\n")
            f.write("PLAN DE MIGRACIÓN: OMNIIRP (Odoo 18) → ODOO 19\n")
            f.write("="*70 + "\n")
            f.write(f"Fecha de análisis: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # Información del servidor origen
            f.write("SERVIDOR ORIGEN (OmniERP)\n")
            f.write("-"*70 + "\n")
            f.write(f"URL: {self.source_info['url']}\n")
            f.write(f"Base de datos: {self.source_info['db']}\n")
            f.write(f"Total módulos: {self.source_info['modules']['total']}\n")
            f.write(f"Módulos personalizados: {len(self.source_info['modules']['custom'])}\n")
            f.write(f"Modelos personalizados: {len(self.source_info['customizations']['custom_models'])}\n")
            f.write("\nVolúmenes de datos:\n")
            for model, count in self.source_info['data_volumes'].items():
                if isinstance(count, int) and count > 0:
                    f.write(f"  - {model}: {count:,} registros\n")
            
            # Información del servidor destino
            f.write("\n\nSERVIDOR DESTINO (Laia.one)\n")
            f.write("-"*70 + "\n")
            f.write(f"URL: {self.target_info['url']}\n")
            f.write(f"Base de datos: {self.target_info['db']}\n")
            f.write(f"Total módulos: {self.target_info['modules']['total']}\n")
            f.write(f"Módulos personalizados: {len(self.target_info['modules']['custom'])}\n")
            
            # Comparación
            f.write("\n\nCOMPARACIÓN\n")
            f.write("-"*70 + "\n")
            f.write(f"Módulos faltantes en destino: {len(comparison['modules_missing_in_target'])}\n")
            if comparison['modules_missing_in_target']:
                f.write("\nMódulos a instalar/verificar:\n")
                for mod in comparison['modules_missing_in_target']:
                    f.write(f"  - {mod}\n")
            
            # Plan de migración
            f.write("\n\nPLAN DE MIGRACIÓN\n")
            f.write("-"*70 + "\n")
            
            f.write("\nPRE-MIGRACIÓN:\n")
            for step in plan['pre_migration']:
                f.write(f"  {step}\n")
            
            f.write("\nPASOS DE MIGRACIÓN:\n")
            for step in plan['migration_steps']:
                f.write(f"  {step}\n")
            
            f.write("\nPOST-MIGRACIÓN:\n")
            for step in plan['post_migration']:
                f.write(f"  {step}\n")
            
            # Riesgos
            f.write("\nRIESGOS IDENTIFICADOS:\n")
            for risk in plan['risks']:
                f.write(f"  ⚠ {risk}\n")
            
            f.write(f"\nTiempo estimado: {plan['estimated_time']}\n")
            
            f.write("\n" + "="*70 + "\n")
            f.write("FIN DEL REPORTE\n")
            f.write("="*70 + "\n")
        
        return report_path
    
    def run_analysis(self):
        """Ejecuta análisis completo"""
        print("\n" + "="*70)
        print("ANÁLISIS DE MIGRACIÓN: OMNIIRP → ODOO 19")
        print("="*70)
        
        # Analizar servidor origen
        self.source_info = self.analyze_server(SOURCE_SERVER)
        if not self.source_info:
            print("\n✗ No se pudo analizar servidor origen. Abortando.")
            return 1
        
        # Analizar servidor destino
        self.target_info = self.analyze_server(TARGET_SERVER)
        if not self.target_info:
            print("\n✗ No se pudo analizar servidor destino. Abortando.")
            return 1
        
        # Comparar servidores
        comparison = self.compare_servers()
        
        # Generar plan
        plan = self.generate_migration_plan(comparison)
        
        # Generar reporte
        report_path = self.generate_report(comparison, plan)
        
        print(f"\n{'='*70}")
        print("ANÁLISIS COMPLETADO")
        print(f"{'='*70}")
        print(f"\n✓ Reporte guardado en: {report_path}")
        print(f"\nResumen:")
        print(f"  - Módulos en origen: {self.source_info['modules']['total']}")
        print(f"  - Módulos en destino: {self.target_info['modules']['total']}")
        print(f"  - Módulos faltantes: {len(comparison['modules_missing_in_target'])}")
        print(f"  - Tiempo estimado: {plan['estimated_time']}")
        
        return 0


def main():
    analyzer = MigrationAnalyzer()
    return analyzer.run_analysis()


if __name__ == "__main__":
    import sys
    sys.exit(main())

