#!/usr/bin/env python3
"""
Meta Análisis de Modelos MCP y Generación de Reporte PDF
Ubicado en: prompts/meta_analysis_mcp_models.py

Este script realiza un análisis completo de todos los modelos accesibles
vía MCP y genera un reporte PDF con las configuraciones, campos, permisos
y relaciones de cada modelo.
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import xmlrpc.client
import ssl
import json

# Intentar importar reportlab, si no está disponible, usar alternativa
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    print("⚠️  reportlab no está instalado. Instalando...")
    import subprocess
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "reportlab", "--quiet"])
        from reportlab.lib.pagesizes import letter, A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
        REPORTLAB_AVAILABLE = True
    except:
        REPORTLAB_AVAILABLE = False

# Configuración de conexión
ODOO_URL = "https://admin.app.controltotal.cloud"
ODOO_DB = "admin_saas"
ODOO_USER = "admin@omnierp.app"
ODOO_API_KEY = "73c3c82596667e2251d374cd5051a3415012683f"

class MCPModelAnalyzer:
    """Analizador de modelos MCP"""
    
    def __init__(self):
        self.context = ssl._create_unverified_context()
        self.common_url = f"{ODOO_URL}/mcp/xmlrpc/common"
        self.object_url = f"{ODOO_URL}/mcp/xmlrpc/object"
        self.common = xmlrpc.client.ServerProxy(self.common_url, context=self.context, allow_none=True)
        self.models = xmlrpc.client.ServerProxy(self.object_url, context=self.context, allow_none=True)
        self.uid = None
        self.enabled_models = []
        self.model_details = {}
        self.model_permissions = {}  # Inicializar siempre
        
    def connect(self):
        """Establece conexión con Odoo"""
        try:
            self.uid = self.common.authenticate(ODOO_DB, ODOO_USER, ODOO_API_KEY, {})
            if self.uid:
                print(f"✓ Conexión establecida. UID: {self.uid}")
                return True
            else:
                print("✗ Error de autenticación")
                return False
        except Exception as e:
            print(f"✗ Error de conexión: {e}")
            return False
    
    def get_enabled_models(self):
        """Obtiene la lista de modelos habilitados para MCP"""
        try:
            # Obtener modelos habilitados desde el endpoint MCP
            import urllib.request
            models_url = f"{ODOO_URL}/mcp/models"
            req = urllib.request.Request(models_url)
            req.add_header("X-API-Key", ODOO_API_KEY)
            
            with urllib.request.urlopen(req, context=self.context, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
                if data.get('success') and 'data' in data:
                    models_list = data['data'].get('models', [])
                    self.enabled_models = [m['model'] for m in models_list]
                    # Obtener permisos para cada modelo
                    for model_name in self.enabled_models:
                        try:
                            access_url = f"{ODOO_URL}/mcp/models/{model_name}/access"
                            access_req = urllib.request.Request(access_url)
                            access_req.add_header("X-API-Key", ODOO_API_KEY)
                            with urllib.request.urlopen(access_req, context=self.context, timeout=10) as access_resp:
                                access_data = json.loads(access_resp.read().decode('utf-8'))
                                if access_data.get('success') and 'data' in access_data:
                                    ops = access_data['data'].get('operations', {})
                                    self.model_permissions[model_name] = {
                                        'read': ops.get('read', False),
                                        'create': ops.get('create', False),
                                        'write': ops.get('write', False),
                                        'unlink': ops.get('unlink', False)
                                    }
                        except:
                            # Si no se pueden obtener permisos, usar valores por defecto
                            self.model_permissions[model_name] = {'read': True, 'create': False, 'write': False, 'unlink': False}
                    print(f"✓ Encontrados {len(self.enabled_models)} modelos habilitados para MCP")
                    return True
        except Exception as e:
            print(f"⚠️  No se pudo obtener lista de modelos desde endpoint MCP: {e}")
            print("   Intentando obtener modelos habilitados directamente...")
        
        # Fallback: intentar obtener desde el modelo mcp.enabled.model
        try:
            enabled_records = self.models.execute_kw(
                ODOO_DB, self.uid, ODOO_API_KEY,
                'mcp.enabled.model', 'search_read',
                [[('active', '=', True)]],
                {'fields': ['model_name', 'allow_read', 'allow_create', 'allow_write', 'allow_unlink']}
            )
            self.enabled_models = [r['model_name'] for r in enabled_records]
            self.model_permissions = {r['model_name']: {
                'read': r.get('allow_read', False),
                'create': r.get('allow_create', False),
                'write': r.get('allow_write', False),
                'unlink': r.get('allow_unlink', False)
            } for r in enabled_records}
            print(f"✓ Encontrados {len(self.enabled_models)} modelos habilitados")
            return True
        except Exception as e:
            print(f"✗ Error al obtener modelos: {e}")
            return False
    
    def analyze_model(self, model_name):
        """Analiza un modelo específico"""
        try:
            # Obtener información de campos
            fields_info = self.models.execute_kw(
                ODOO_DB, self.uid, ODOO_API_KEY,
                model_name, 'fields_get',
                [],
                {'attributes': ['string', 'type', 'required', 'readonly', 'relation', 'help']}
            )
            
            # Contar registros
            try:
                count = self.models.execute_kw(
                    ODOO_DB, self.uid, ODOO_API_KEY,
                    model_name, 'search_count', [[]]
                )
            except:
                count = 0
            
            # Obtener permisos si están disponibles
            permissions = self.model_permissions.get(model_name, {})
            
            return {
                'name': model_name,
                'fields': fields_info,
                'field_count': len(fields_info),
                'record_count': count,
                'permissions': permissions
            }
        except Exception as e:
            print(f"  ⚠️  Error al analizar {model_name}: {e}")
            return None
    
    def analyze_all_models(self):
        """Analiza todos los modelos habilitados"""
        print(f"\n📊 Analizando {len(self.enabled_models)} modelos...")
        self.model_details = {}
        
        for i, model_name in enumerate(self.enabled_models, 1):
            print(f"  [{i}/{len(self.enabled_models)}] Analizando {model_name}...", end=' ')
            details = self.analyze_model(model_name)
            if details:
                self.model_details[model_name] = details
                print(f"✓ ({details['field_count']} campos, {details['record_count']} registros)")
            else:
                print("✗")
        
        print(f"\n✓ Análisis completado: {len(self.model_details)} modelos analizados")
        return self.model_details

class PDFReportGenerator:
    """Generador de reportes PDF"""
    
    def __init__(self, analyzer, output_path):
        self.analyzer = analyzer
        self.output_path = output_path
        self.doc = None
        self.story = []
        self.styles = None
        
    def create_styles(self):
        """Crea estilos para el PDF"""
        self.styles = getSampleStyleSheet()
        
        # Título principal
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=30,
            alignment=TA_CENTER
        ))
        
        # Subtítulo
        self.styles.add(ParagraphStyle(
            name='CustomHeading2',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#2c3e50'),
            spaceAfter=12,
            spaceBefore=20
        ))
        
        # Título de sección
        self.styles.add(ParagraphStyle(
            name='SectionTitle',
            parent=self.styles['Heading3'],
            fontSize=14,
            textColor=colors.HexColor('#34495e'),
            spaceAfter=10,
            spaceBefore=15,
            backColor=colors.HexColor('#ecf0f1'),
            borderPadding=8
        ))
    
    def generate_report(self):
        """Genera el reporte PDF completo"""
        if not REPORTLAB_AVAILABLE:
            print("✗ reportlab no está disponible. No se puede generar PDF.")
            return False
        
        print(f"\n📄 Generando reporte PDF: {self.output_path}")
        
        self.doc = SimpleDocTemplate(
            self.output_path,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )
        
        self.create_styles()
        self.story = []
        
        # Portada
        self.add_cover_page()
        self.story.append(PageBreak())
        
        # Resumen ejecutivo
        self.add_executive_summary()
        self.story.append(PageBreak())
        
        # Detalles por modelo
        self.add_model_details()
        
        # Construir PDF
        self.doc.build(self.story)
        print(f"✓ Reporte generado exitosamente: {self.output_path}")
        return True
    
    def add_cover_page(self):
        """Agrega la portada del reporte"""
        self.story.append(Spacer(1, 2*inch))
        self.story.append(Paragraph("META ANÁLISIS DE MODELOS MCP", self.styles['CustomTitle']))
        self.story.append(Spacer(1, 0.5*inch))
        self.story.append(Paragraph("Reporte de Configuración y Accesos", self.styles['Heading2']))
        self.story.append(Spacer(1, 1*inch))
        
        # Información del servidor
        info_data = [
            ['Servidor:', ODOO_URL],
            ['Base de Datos:', ODOO_DB],
            ['Usuario:', ODOO_USER],
            ['Fecha de Generación:', datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
            ['Versión MCP Server:', '19.0.1.0.0'],
        ]
        
        info_table = Table(info_data, colWidths=[2*inch, 4*inch])
        info_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
        ]))
        self.story.append(info_table)
        
        self.story.append(Spacer(1, 1*inch))
        self.story.append(Paragraph(
            "Este reporte contiene un análisis completo de todos los modelos "
            "accesibles vía Model Context Protocol (MCP) en este servidor de control.",
            self.styles['Normal']
        ))
    
    def add_executive_summary(self):
        """Agrega el resumen ejecutivo"""
        self.story.append(Paragraph("RESUMEN EJECUTIVO", self.styles['CustomHeading2']))
        self.story.append(Spacer(1, 0.3*inch))
        
        total_models = len(self.analyzer.model_details)
        total_fields = sum(m['field_count'] for m in self.analyzer.model_details.values())
        total_records = sum(m['record_count'] for m in self.analyzer.model_details.values())
        
        summary_data = [
            ['Métrica', 'Valor'],
            ['Total de Modelos Habilitados', str(total_models)],
            ['Total de Campos', str(total_fields)],
            ['Total de Registros', f"{total_records:,}"],
            ['Modelos con Permisos de Lectura', str(sum(1 for m in self.analyzer.model_details.values() if m['permissions'].get('read')))],
            ['Modelos con Permisos de Escritura', str(sum(1 for m in self.analyzer.model_details.values() if m['permissions'].get('write')))],
            ['Modelos con Permisos de Creación', str(sum(1 for m in self.analyzer.model_details.values() if m['permissions'].get('create')))],
            ['Modelos con Permisos de Eliminación', str(sum(1 for m in self.analyzer.model_details.values() if m['permissions'].get('unlink')))],
        ]
        
        summary_table = Table(summary_data, colWidths=[3.5*inch, 2.5*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ]))
        self.story.append(summary_table)
        
        # Lista de modelos
        self.story.append(Spacer(1, 0.3*inch))
        self.story.append(Paragraph("Modelos Habilitados:", self.styles['SectionTitle']))
        
        model_list = []
        for model_name, details in sorted(self.analyzer.model_details.items()):
            perms = []
            if details['permissions'].get('read'): perms.append('R')
            if details['permissions'].get('create'): perms.append('C')
            if details['permissions'].get('write'): perms.append('W')
            if details['permissions'].get('unlink'): perms.append('D')
            perms_str = ''.join(perms) if perms else 'Ninguno'
            
            model_list.append([
                model_name,
                str(details['field_count']),
                f"{details['record_count']:,}",
                perms_str
            ])
        
        model_table = Table(
            [['Modelo', 'Campos', 'Registros', 'Permisos']] + model_list,
            colWidths=[2.5*inch, 1*inch, 1.2*inch, 1.3*inch]
        )
        model_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (2, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ]))
        self.story.append(model_table)
    
    def add_model_details(self):
        """Agrega detalles de cada modelo"""
        self.story.append(Paragraph("DETALLES POR MODELO", self.styles['CustomHeading2']))
        self.story.append(Spacer(1, 0.3*inch))
        
        for model_name, details in sorted(self.analyzer.model_details.items()):
            # Título del modelo
            self.story.append(Paragraph(f"Modelo: {model_name}", self.styles['SectionTitle']))
            
            # Información básica
            info_text = f"""
            <b>Campos:</b> {details['field_count']} | 
            <b>Registros:</b> {details['record_count']:,} | 
            <b>Permisos:</b> {self._format_permissions(details['permissions'])}
            """
            self.story.append(Paragraph(info_text, self.styles['Normal']))
            self.story.append(Spacer(1, 0.2*inch))
            
            # Campos del modelo (limitado a los primeros 20 para no hacer el PDF muy largo)
            fields = list(details['fields'].items())[:20]
            if fields:
                self.story.append(Paragraph("Campos Principales:", self.styles['Heading4']))
                
                field_data = [['Campo', 'Tipo', 'Requerido', 'Solo Lectura', 'Relación']]
                for field_name, field_info in fields:
                    field_data.append([
                        field_name,
                        field_info.get('type', 'N/A'),
                        'Sí' if field_info.get('required', False) else 'No',
                        'Sí' if field_info.get('readonly', False) else 'No',
                        field_info.get('relation', 'N/A') if field_info.get('type') == 'many2one' else '-'
                    ])
                
                field_table = Table(field_data, colWidths=[1.5*inch, 1*inch, 0.8*inch, 0.8*inch, 1.9*inch])
                field_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 9),
                    ('FONTSIZE', (0, 1), (-1, -1), 8),
                    ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
                ]))
                self.story.append(field_table)
                
                if len(details['fields']) > 20:
                    self.story.append(Paragraph(
                        f"<i>... y {len(details['fields']) - 20} campos más</i>",
                        self.styles['Normal']
                    ))
            
            self.story.append(Spacer(1, 0.3*inch))
            self.story.append(PageBreak())
    
    def _format_permissions(self, perms):
        """Formatea los permisos para mostrar"""
        perm_list = []
        if perms.get('read'): perm_list.append('Lectura')
        if perms.get('create'): perm_list.append('Crear')
        if perms.get('write'): perm_list.append('Escribir')
        if perms.get('unlink'): perm_list.append('Eliminar')
        return ', '.join(perm_list) if perm_list else 'Ninguno'

def main():
    """Función principal"""
    print("=" * 70)
    print("META ANÁLISIS DE MODELOS MCP")
    print("=" * 70)
    
    # Crear analizador
    analyzer = MCPModelAnalyzer()
    
    # Conectar
    if not analyzer.connect():
        return 1
    
    # Obtener modelos habilitados
    if not analyzer.get_enabled_models():
        return 1
    
    # Analizar todos los modelos
    analyzer.analyze_all_models()
    
    # Generar reporte PDF
    output_dir = Path(__file__).parent.parent / "reports"
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"mcp_models_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    
    generator = PDFReportGenerator(analyzer, str(output_file))
    if generator.generate_report():
        print(f"\n✓ Reporte guardado en: {output_file}")
        return 0
    else:
        return 1

if __name__ == "__main__":
    sys.exit(main())

