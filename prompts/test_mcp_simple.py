#!/usr/bin/env python3
"""
Script simple de prueba para el cliente MCP usando conexión directa XML-RPC
Ubicado en: prompts/test_mcp_simple.py

Este script realiza pruebas básicas de conexión y consultas a Odoo
usando los endpoints MCP XML-RPC.
"""

import xmlrpc.client
import ssl

# Configuración
ODOO_URL = "https://admin.app.controltotal.cloud"
ODOO_DB = "admin_saas"
ODOO_USER = "admin@omnierp.app"
ODOO_API_KEY = "73c3c82596667e2251d374cd5051a3415012683f"

def test_connection():
    """Prueba la conexión básica"""
    print("=" * 60)
    print("PRUEBA 1: Conexión con Odoo")
    print("=" * 60)
    
    try:
        # Crear contexto SSL que acepta certificados autofirmados
        context = ssl._create_unverified_context()
        
        # Endpoints MCP
        common_url = f"{ODOO_URL}/mcp/xmlrpc/common"
        object_url = f"{ODOO_URL}/mcp/xmlrpc/object"
        
        print(f"URL: {ODOO_URL}")
        print(f"Base de datos: {ODOO_DB}")
        print(f"Endpoint común: {common_url}")
        print(f"Endpoint objeto: {object_url}")
        
        # Probar endpoint de health primero
        import urllib.request
        health_url = f"{ODOO_URL}/mcp/health"
        print(f"\nProbando health endpoint: {health_url}")
        
        try:
            req = urllib.request.Request(health_url)
            with urllib.request.urlopen(req, context=context, timeout=10) as response:
                health_data = response.read().decode('utf-8')
                print(f"✓ Health check exitoso: {health_data[:200]}")
        except Exception as e:
            print(f"⚠ Health check falló: {e}")
        
        # Conectar usando XML-RPC
        print(f"\nConectando vía XML-RPC...")
        common = xmlrpc.client.ServerProxy(common_url, context=context, allow_none=True)
        models = xmlrpc.client.ServerProxy(object_url, context=context, allow_none=True)
        
        # Autenticar usando API key
        print("Autenticando con API key...")
        uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_API_KEY, {})
        
        if uid:
            print(f"✓ Autenticación exitosa! UID: {uid}")
            return models, uid
        else:
            print("✗ Error: Autenticación fallida")
            return None, None
            
    except Exception as e:
        print(f"✗ Error de conexión: {e}")
        import traceback
        traceback.print_exc()
        return None, None

def test_search_products(models, uid):
    """Prueba búsqueda de productos"""
    print("\n" + "=" * 60)
    print("PRUEBA 2: Búsqueda de Productos")
    print("=" * 60)
    
    try:
        print("\nBuscando productos vendibles...")
        products = models.execute_kw(
            ODOO_DB, uid, ODOO_API_KEY,
            'product.product', 'search_read',
            [[('sale_ok', '=', True)]],
            {'fields': ['name', 'list_price', 'qty_available'], 'limit': 5}
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

def test_search_partners(models, uid):
    """Prueba búsqueda de terceros"""
    print("\n" + "=" * 60)
    print("PRUEBA 3: Búsqueda de Terceros (Partners)")
    print("=" * 60)
    
    try:
        print("\nBuscando terceros (clientes)...")
        partners = models.execute_kw(
            ODOO_DB, uid, ODOO_API_KEY,
            'res.partner', 'search_read',
            [[('customer_rank', '>', 0)]],
            {'fields': ['name', 'email', 'phone', 'city'], 'limit': 5}
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

def test_count_products(models, uid):
    """Prueba conteo de productos"""
    print("\n" + "=" * 60)
    print("PRUEBA 4: Conteo de Productos")
    print("=" * 60)
    
    try:
        total = models.execute_kw(
            ODOO_DB, uid, ODOO_API_KEY,
            'product.product', 'search_count', [[]]
        )
        
        saleable = models.execute_kw(
            ODOO_DB, uid, ODOO_API_KEY,
            'product.product', 'search_count',
            [[('sale_ok', '=', True)]]
        )
        
        print(f"✓ Total de productos: {total}")
        print(f"✓ Productos vendibles: {saleable}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error al contar productos: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_count_partners(models, uid):
    """Prueba conteo de terceros"""
    print("\n" + "=" * 60)
    print("PRUEBA 5: Conteo de Terceros")
    print("=" * 60)
    
    try:
        total = models.execute_kw(
            ODOO_DB, uid, ODOO_API_KEY,
            'res.partner', 'search_count', [[]]
        )
        
        customers = models.execute_kw(
            ODOO_DB, uid, ODOO_API_KEY,
            'res.partner', 'search_count',
            [[('customer_rank', '>', 0)]]
        )
        
        suppliers = models.execute_kw(
            ODOO_DB, uid, ODOO_API_KEY,
            'res.partner', 'search_count',
            [[('supplier_rank', '>', 0)]]
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
    print(f"  URL: {ODOO_URL}")
    print(f"  Base de datos: {ODOO_DB}")
    print(f"  Usuario: {ODOO_USER}")
    print(f"  API Key: {ODOO_API_KEY[:20]}...")
    
    # Prueba de conexión
    models, uid = test_connection()
    
    if not models or not uid:
        print("\n✗ No se pudo establecer conexión. Abortando pruebas.")
        return 1
    
    # Ejecutar pruebas
    results = []
    results.append(("Búsqueda de Productos", test_search_products(models, uid)))
    results.append(("Búsqueda de Terceros", test_search_partners(models, uid)))
    results.append(("Conteo de Productos", test_count_products(models, uid)))
    results.append(("Conteo de Terceros", test_count_partners(models, uid)))
    
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
    import sys
    sys.exit(main())

