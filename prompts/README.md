# Scripts de Consultas y Pruebas MCP

Este directorio contiene todos los scripts de consultas y pruebas para el cliente MCP de Odoo.

## Scripts Disponibles

### 1. `test_laia_server.py`
**Nuevo** - Script de prueba para el servidor MCP de Laia.one

Este script prueba la conexión y realiza consultas al servidor MCP configurado en `https://laia.one`.

**Configuración:**
- URL: `https://laia.one`
- Base de datos: `admin-laia`
- Usuario: `admin@laia.one`
- API Key: Configurada en el script

**Características:**
- Transport XML-RPC personalizado que envía el header `X-Odoo-Database` (necesario para servidores multi-database)
- Pruebas de conexión y autenticación
- Búsqueda y conteo de productos
- Búsqueda y conteo de terceros (partners)

**Uso:**
```bash
python3 prompts/test_laia_server.py
```

### 2. `test_mcp_simple.py`
Script simple de prueba para el cliente MCP usando conexión directa XML-RPC.

**Uso:**
```bash
cd prompts
python3 test_mcp_simple.py
```

**Funcionalidades:**
- Prueba de conexión con Odoo
- Búsqueda de productos
- Búsqueda de terceros (partners)
- Conteo de productos y terceros

### 2. `analyze_saas_plans.py`
Análisis completo de SaaS Plans en la base de datos Odoo.

**Uso:**
```bash
cd prompts
python3 analyze_saas_plans.py
```

**Funcionalidades:**
- Identificación de productos SaaS Plans
- Análisis de precios y categorización
- Estadísticas y recomendaciones

### 3. `test_mcp_client.py`
Script de prueba usando el cliente MCP oficial (requiere Python 3.10+).

**Uso:**
```bash
cd prompts
python3 test_mcp_client.py
```

**Nota:** Este script requiere el cliente MCP instalado y Python 3.10 o superior.

### 4. `meta_analysis_mcp_models.py`
Meta análisis completo de todos los modelos accesibles vía MCP y generación de reporte PDF.

**Uso:**
```bash
cd prompts
python3 meta_analysis_mcp_models.py
```

**Funcionalidades:**
- Lista todos los modelos habilitados para MCP
- Analiza campos, permisos y configuraciones de cada modelo
- Genera un reporte PDF completo con toda la información
- Incluye resumen ejecutivo y detalles por modelo

**Salida:**
- El reporte PDF se guarda en `../reports/mcp_models_analysis_YYYYMMDD_HHMMSS.pdf`

**Dependencias:**
- `reportlab` (se instala automáticamente si no está disponible)

## Configuración

Todos los scripts utilizan las siguientes credenciales (configuradas en cada script):

- **URL:** https://admin.app.controltotal.cloud
- **Base de datos:** admin_saas
- **Usuario:** admin@omnierp.app
- **API Key:** 73c3c82596667e2251d374cd5051a3415012683f

## Estructura

```
prompts/
├── README.md                    # Este archivo
├── test_mcp_simple.py          # Pruebas básicas XML-RPC
├── test_mcp_client.py          # Pruebas con cliente MCP oficial
└── analyze_saas_plans.py       # Análisis de planes SaaS
```

## Notas

- Los scripts están diseñados para ejecutarse desde el directorio `prompts/`
- Todos los scripts incluyen manejo de errores y mensajes informativos
- Los scripts usan conexiones SSL no verificadas para desarrollo/testing

## Agregar Nuevos Scripts

Al crear nuevos scripts de consulta:

1. Guardarlos en este directorio `prompts/`
2. Incluir el shebang `#!/usr/bin/env python3`
3. Agregar documentación en el header del archivo
4. Actualizar este README con la descripción del nuevo script
5. Usar las credenciales estándar o permitir configuración mediante variables de entorno

