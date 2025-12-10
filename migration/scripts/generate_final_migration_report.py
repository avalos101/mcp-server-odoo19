#!/usr/bin/env python3
"""
Generador de Reporte Final de Migración
Ubicado en: prompts/generate_final_migration_report.py
"""

import subprocess
import xmlrpc.client
import ssl
import urllib.request
from datetime import datetime
from pathlib import Path

SOURCE = {
    'url': 'https://omnierp.app',
    'db': 'omnierp.app',
    'user': 'admin@omnierp.app',
    'key': '7f3ea49d0339de71e39996866b61c26416ba0597',
    'ssh': 'diego.avalos@omnierp.app'
}

TARGET = {
    'url': 'https://laia.one',
    'db': 'omnierp_migrated',
    'user': 'admin@laia.one',
    'key': 'cfebea4c6d0a3cc3e345db4aa9c94b3e085ea3e5',
    'ssh': 'diego.avalos@laia.one'
}

def ssh_exec(cmd, host):
    ssh_cmd = ['ssh', '-o', 'StrictHostKeyChecking=no', host, cmd]
    try:
        result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=60)
        return result.returncode == 0, result.stdout, result.stderr
    except:
        return False, "", ""

def get_counts_via_sql(ssh, db, models):
    """Obtiene conteos vía SQL"""
    counts = {}
    for model, table in models.items():
        cmd = f"sudo -u postgres psql -d '{db}' -t -c \"SELECT COUNT(*) FROM {table};\""
        success, out, _ = ssh_exec(cmd, ssh)
        if success and out.strip():
            try:
                counts[model] = int(out.strip())
            except:
                counts[model] = 0
        else:
            counts[model] = 0
    return counts

def get_counts_via_mcp(url, db, user, key, models):
    """Obtiene conteos vía MCP"""
    counts = {}
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
        models_obj = xmlrpc.client.ServerProxy(f"{url}/mcp/xmlrpc/object", transport=transport, allow_none=True)
        uid = common.authenticate(db, user, key, {})
        
        if uid:
            for model in models.keys():
                try:
                    count = models_obj.execute_kw(db, uid, key, model, 'search_count', [[]])
                    counts[model] = count
                except:
                    counts[model] = 0
    except:
        pass
    
    return counts

def main():
    print("="*70)
    print("GENERANDO REPORTE FINAL DE MIGRACIÓN")
    print("="*70)
    
    models_map = {
        'res.partner': 'res_partner',
        'product.template': 'product_template',
        'product.product': 'product_product',
        'crm.lead': 'crm_lead',
        'sale.order': 'sale_order',
        'account.move': 'account_move',
        'project.project': 'project_project',
        'project.task': 'project_task',
        'knowledge.article': 'knowledge_article',
        'helpdesk.ticket': 'helpdesk_ticket',
    }
    
    # Obtener conteos origen
    print("\nObteniendo conteos de origen...")
    source_counts = get_counts_via_mcp(SOURCE['url'], SOURCE['db'], SOURCE['user'], SOURCE['key'], models_map)
    
    # Obtener conteos destino
    print("Obteniendo conteos de destino...")
    target_counts = get_counts_via_sql(TARGET['ssh'], TARGET['db'], models_map)
    
    # Generar reporte
    report_file = Path(__file__).parent.parent / "reports" / f"FINAL_MIGRATION_REPORT_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("="*80 + "\n")
        f.write("REPORTE FINAL DE MIGRACIÓN DE DATOS\n")
        f.write("="*80 + "\n")
        f.write(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("COMPARACIÓN DE DATOS MIGRADOS\n")
        f.write("-"*80 + "\n")
        f.write(f"{'Modelo':<30} {'Origen':<15} {'Destino':<15} {'%':<10} {'Estado':<10}\n")
        f.write("-"*80 + "\n")
        
        total_source = 0
        total_target = 0
        
        for model, table in models_map.items():
            source_count = source_counts.get(model, 0)
            target_count = target_counts.get(model, 0)
            total_source += source_count
            total_target += target_count
            
            if source_count > 0:
                percentage = (target_count / source_count) * 100
            else:
                percentage = 0
            
            status = "✓" if target_count > 0 else "⚠"
            if percentage >= 90:
                status = "✓✓"
            elif percentage >= 50:
                status = "✓"
            elif percentage > 0:
                status = "⚠"
            else:
                status = "✗"
            
            f.write(f"{model:<30} {source_count:<15,} {target_count:<15,} {percentage:>6.1f}% {status:<10}\n")
        
        f.write("-"*80 + "\n")
        f.write(f"{'TOTAL':<30} {total_source:<15,} {total_target:<15,} {(total_target/total_source*100) if total_source > 0 else 0:>6.1f}%\n\n")
        
        f.write("RESUMEN\n")
        f.write("-"*80 + "\n")
        f.write(f"Total registros en origen: {total_source:,}\n")
        f.write(f"Total registros migrados: {total_target:,}\n")
        f.write(f"Porcentaje migrado: {(total_target/total_source*100) if total_source > 0 else 0:.1f}%\n\n")
        
        f.write("ESTADO POR MODELO\n")
        f.write("-"*80 + "\n")
        for model, table in models_map.items():
            source_count = source_counts.get(model, 0)
            target_count = target_counts.get(model, 0)
            if source_count > 0:
                f.write(f"{model}: {target_count:,}/{source_count:,} ({(target_count/source_count*100):.1f}%)\n")
        
        f.write("\n" + "="*80 + "\n")
        f.write("FIN DEL REPORTE\n")
        f.write("="*80 + "\n")
    
    print(f"✓ Reporte generado: {report_file}")
    
    # Mostrar resumen
    with open(report_file, 'r') as f:
        print("\n" + f.read())

if __name__ == "__main__":
    main()

