#!/usr/bin/env python3
"""
Script de prueba para el cliente MCP de Odoo
Ubicado en: prompts/test_mcp_client.py

Prueba la conexión y realiza consultas de productos y terceros
usando el cliente MCP oficial (requiere Python 3.10+).
"""

import os
import sys
from pathlib import Path

# Agregar el directorio del cliente MCP al path
mcp_client_path = Path(__file__).parent / "mcp-client"
sys.path.insert(0, str(mcp_client_path))

from mcp_server_odoo.config import OdooConfig, load_config
from mcp_server_odoo.odoo_connection import OdooConnection

# Configuración
CONFIG = {
    "ODOO_URL": "https://admin.app.controltotal.cloud",
    "ODOO_API_KEY": "73c3c82596667e2251d374cd5051a3415012683f",
    "ODOO_DB": "admin_saas",
    "ODOO_USER": "admin@omnierp.app",
}

def test_connection():
    """Prueba la conexión básica con Odoo"""
    print("=" * 60)
    print("PRUEBA 1: Conexión con Odoo")
    print("=" * 60)
    
    try:
        # Configurar variables de entorno
        for key, value in CONFIG.items():
            os.environ[key] = value
        
        # Cargar configuración
        config = load_config()
        print(f"✓ URL configurada: {config.url}")
        print(f"✓ Base de datos: {config.database}")
        print(f"✓ API Key configurada: {'Sí' if config.api_key else 'No'}")
        
        # Crear conexión
        connection = OdooConnection(config)
        
        # Probar conexión
        print("\nProbando conexión...")
        health = connection.check_health()
        
        if health:
            print("✓ Conexión exitosa!")
            print(f"  - Servidor: {health.get('server', 'N/A')}")
            print(f"  - Versión Odoo: {health.get('version', 'N/A')}")
            return connection, config
        else:
            print("✗ Error: No se pudo establecer conexión")
            return None, None
            
    except Exception as e:
        print(f"✗ Error de conexión: {e}")
        import traceback
        traceback.print_exc()
        return None, None

def test_search_products(connection: OdooConnection):
    """Prueba búsqueda de productos"""
    print("\n" + "=" * 60)
    print("PRUEBA 2: Búsqueda de Productos")
    print("=" * 60)
    
    try:
        # Buscar productos
        print("\nBuscando productos...")
        products = connection.execute_kw(
            "product.product",
            "search_read",
            [[("sale_ok", "=", True)]],
            {"fields": ["name", "list_price", "qty_available"], "limit": 5}
        )
        
        if products:
            print(f"✓ Encontrados {len(products)} productos:")
            for i, product in enumerate(products, 1):
                print(f"\n  Producto {i}:")
                print(f"    - Nombre: {product.get('name', 'N/A')}")
                print(f"    - Precio: ${product.get('list_price', 0):.2f}")
                print(f"    - Stock: {product.get('qty_available', 0)}")
        else:
            print("⚠ No se encontraron productos")
            
        return True
        
    except Exception as e:
        print(f"✗ Error al buscar productos: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_search_partners(connection: OdooConnection):
    """Prueba búsqueda de terceros (partners)"""
    print("\n" + "=" * 60)
    print("PRUEBA 3: Búsqueda de Terceros (Partners)")
    print("=" * 60)
    
    try:
        # Buscar partners (clientes)
        print("\nBuscando terceros (clientes)...")
        partners = connection.execute_kw(
            "res.partner",
            "search_read",
            [[("customer_rank", ">", 0)]],
            {"fields": ["name", "email", "phone", "city"], "limit": 5}
        )
        
        if partners:
            print(f"✓ Encontrados {len(partners)} terceros:")
            for i, partner in enumerate(partners, 1):
                print(f"\n  Tercero {i}:")
                print(f"    - Nombre: {partner.get('name', 'N/A')}")
                print(f"    - Email: {partner.get('email', 'N/A')}")
                print(f"    - Teléfono: {partner.get('phone', 'N/A')}")
                print(f"    - Ciudad: {partner.get('city', 'N/A')}")
        else:
            print("⚠ No se encontraron terceros")
            
        return True
        
    except Exception as e:
        print(f"✗ Error al buscar terceros: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_count_products(connection: OdooConnection):
    """Prueba conteo de productos"""
    print("\n" + "=" * 60)
    print("PRUEBA 4: Conteo de Productos")
    print("=" * 60)
    
    try:
        # Contar productos totales
        total = connection.execute_kw(
            "product.product",
            "search_count",
            [[]]
        )
        
        # Contar productos vendibles
        saleable = connection.execute_kw(
            "product.product",
            "search_count",
            [[("sale_ok", "=", True)]]
        )
        
        print(f"✓ Total de productos: {total}")
        print(f"✓ Productos vendibles: {saleable}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error al contar productos: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_count_partners(connection: OdooConnection):
    """Prueba conteo de terceros"""
    print("\n" + "=" * 60)
    print("PRUEBA 5: Conteo de Terceros")
    print("=" * 60)
    
    try:
        # Contar partners totales
        total = connection.execute_kw(
            "res.partner",
            "search_count",
            [[]]
        )
        
        # Contar clientes
        customers = connection.execute_kw(
            "res.partner",
            "search_count",
            [[("customer_rank", ">", 0)]]
        )
        
        # Contar proveedores
        suppliers = connection.execute_kw(
            "res.partner",
            "search_count",
            [[("supplier_rank", ">", 0)]]
        )
        
        print(f"✓ Total de terceros: {total}")
        print(f"✓ Clientes: {customers}")
        print(f"✓ Proveedores: {suppliers}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error al contar terceros: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Función principal"""
    print("\n" + "=" * 60)
    print("PRUEBAS DEL CLIENTE MCP PARA ODOO")
    print("=" * 60)
    print(f"\nConfiguración:")
    print(f"  URL: {CONFIG['ODOO_URL']}")
    print(f"  Base de datos: {CONFIG['ODOO_DB']}")
    print(f"  Usuario: {CONFIG['ODOO_USER']}")
    print(f"  API Key: {CONFIG['ODOO_API_KEY'][:20]}...")
    
    # Prueba de conexión
    connection, config = test_connection()
    
    if not connection:
        print("\n✗ No se pudo establecer conexión. Abortando pruebas.")
        return 1
    
    # Ejecutar pruebas
    results = []
    results.append(("Búsqueda de Productos", test_search_products(connection)))
    results.append(("Búsqueda de Terceros", test_search_partners(connection)))
    results.append(("Conteo de Productos", test_count_products(connection)))
    results.append(("Conteo de Terceros", test_count_partners(connection)))
    
    # Resumen
    print("\n" + "=" * 60)
    print("RESUMEN DE PRUEBAS")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} pruebas exitosas")
    
    if passed == total:
        print("\n✓ Todas las pruebas pasaron exitosamente!")
        return 0
    else:
        print(f"\n⚠ {total - passed} prueba(s) fallaron")
        return 1

if __name__ == "__main__":
    sys.exit(main())

