#!/bin/bash
# Script para instalar mcp_server en el servidor Odoo
# Ejecutar en el servidor: bash install_on_server.sh

set -e

echo "=========================================="
echo "Instalación de MCP Server para Odoo 19"
echo "=========================================="

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Variables
REPO_URL="https://github.com/avalos101/mcp-server-odoo19.git"
INSTALL_DIR="/opt/mcp-server-odoo19"
ODOO_CONFIG="/etc/odoo/odoo.conf"
ODOO_USER="odoo"
ODOO_ADDONS_PATH=""

# Función para imprimir mensajes
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Verificar si se ejecuta como root o con sudo
if [ "$EUID" -ne 0 ]; then 
    print_warn "Este script necesita privilegios de root. Usando sudo..."
    SUDO="sudo"
else
    SUDO=""
fi

# 1. Verificar si git está instalado
print_info "Verificando dependencias..."
if ! command -v git &> /dev/null; then
    print_error "git no está instalado. Instalando..."
    $SUDO apt-get update
    $SUDO apt-get install -y git
fi

# 2. Crear directorio de instalación
print_info "Creando directorio de instalación: $INSTALL_DIR"
$SUDO mkdir -p $INSTALL_DIR
$SUDO chown $USER:$USER $INSTALL_DIR 2>/dev/null || $SUDO chown $ODOO_USER:$ODOO_USER $INSTALL_DIR

# 3. Clonar o actualizar el repositorio
if [ -d "$INSTALL_DIR/.git" ]; then
    print_info "El repositorio ya existe. Actualizando..."
    cd $INSTALL_DIR
    git pull origin main
else
    print_info "Clonando repositorio desde GitHub..."
    cd /opt
    $SUDO git clone $REPO_URL $INSTALL_DIR
    $SUDO chown -R $ODOO_USER:$ODOO_USER $INSTALL_DIR
fi

# 4. Verificar que el módulo existe
if [ ! -d "$INSTALL_DIR/mcp_server" ]; then
    print_error "El módulo mcp_server no se encontró en $INSTALL_DIR"
    exit 1
fi

print_info "Módulo encontrado en: $INSTALL_DIR/mcp_server"

# 5. Buscar archivo de configuración de Odoo
print_info "Buscando archivo de configuración de Odoo..."

# Posibles ubicaciones del archivo de configuración
CONFIG_LOCATIONS=(
    "/etc/odoo/odoo.conf"
    "/etc/odoo.conf"
    "/opt/odoo/odoo.conf"
    "/home/$ODOO_USER/odoo.conf"
    "$(find /opt /etc /home -name odoo.conf 2>/dev/null | head -1)"
)

ODOO_CONFIG=""
for loc in "${CONFIG_LOCATIONS[@]}"; do
    if [ -f "$loc" ]; then
        ODOO_CONFIG="$loc"
        print_info "Archivo de configuración encontrado: $ODOO_CONFIG"
        break
    fi
done

if [ -z "$ODOO_CONFIG" ]; then
    print_error "No se encontró el archivo de configuración de Odoo"
    print_warn "Por favor, especifica la ruta manualmente o crea el archivo"
    exit 1
fi

# 6. Hacer backup del archivo de configuración
print_info "Creando backup del archivo de configuración..."
$SUDO cp $ODOO_CONFIG ${ODOO_CONFIG}.backup.$(date +%Y%m%d_%H%M%S)

# 7. Leer la ruta actual de addons_path
print_info "Leyendo configuración actual..."
CURRENT_ADDONS_PATH=$($SUDO grep "^addons_path" $ODOO_CONFIG | cut -d'=' -f2 | tr -d ' ' || echo "")

if [ -z "$CURRENT_ADDONS_PATH" ]; then
    # Si no existe, crear una nueva línea
    print_warn "No se encontró addons_path. Se agregará uno nuevo."
    NEW_ADDONS_PATH="/opt/odoo/addons,$INSTALL_DIR"
else
    # Verificar si la ruta ya está incluida
    if echo "$CURRENT_ADDONS_PATH" | grep -q "$INSTALL_DIR"; then
        print_info "La ruta del módulo ya está en addons_path"
        NEW_ADDONS_PATH="$CURRENT_ADDONS_PATH"
    else
        print_info "Agregando ruta del módulo a addons_path..."
        NEW_ADDONS_PATH="$CURRENT_ADDONS_PATH,$INSTALL_DIR"
    fi
fi

# 8. Actualizar el archivo de configuración
print_info "Actualizando archivo de configuración..."
$SUDO sed -i.bak "s|^addons_path.*|addons_path = $NEW_ADDONS_PATH|" $ODOO_CONFIG

# Verificar que se actualizó correctamente
if $SUDO grep -q "^addons_path.*$INSTALL_DIR" $ODOO_CONFIG; then
    print_info "✓ Archivo de configuración actualizado correctamente"
    print_info "  addons_path = $NEW_ADDONS_PATH"
else
    # Si no se actualizó, agregar manualmente
    print_warn "Intentando agregar addons_path manualmente..."
    if ! $SUDO grep -q "^addons_path" $ODOO_CONFIG; then
        $SUDO bash -c "echo 'addons_path = $NEW_ADDONS_PATH' >> $ODOO_CONFIG"
    fi
fi

# 9. Verificar permisos del módulo
print_info "Verificando permisos..."
$SUDO chown -R $ODOO_USER:$ODOO_USER $INSTALL_DIR
$SUDO chmod -R 755 $INSTALL_DIR

# 10. Buscar el ejecutable de Odoo
print_info "Buscando ejecutable de Odoo..."
ODOO_BIN=""
BIN_LOCATIONS=(
    "/usr/bin/odoo-bin"
    "/opt/odoo/odoo/odoo-bin"
    "/opt/odoo/odoo-bin"
    "$(which odoo-bin 2>/dev/null)"
    "$(find /opt /usr -name odoo-bin 2>/dev/null | head -1)"
)

for loc in "${BIN_LOCATIONS[@]}"; do
    if [ -f "$loc" ] && [ -x "$loc" ]; then
        ODOO_BIN="$loc"
        print_info "Ejecutable de Odoo encontrado: $ODOO_BIN"
        break
    fi
done

if [ -z "$ODOO_BIN" ]; then
    print_error "No se encontró el ejecutable de Odoo (odoo-bin)"
    print_warn "Necesitarás especificar la ruta manualmente para instalar el módulo"
    exit 1
fi

# 11. Buscar base de datos de pruebas
print_info "Buscando bases de datos disponibles..."
DB_LIST=$($SUDO -u $ODOO_USER $ODOO_BIN --help | grep -i database || echo "")
TEST_DB=""

# Intentar encontrar base de datos de pruebas
if [ -f "/etc/odoo/odoo.conf" ]; then
    TEST_DB=$($SUDO grep "^db_name" /etc/odoo/odoo.conf | cut -d'=' -f2 | tr -d ' ' || echo "")
fi

if [ -z "$TEST_DB" ]; then
    print_warn "No se encontró base de datos en la configuración"
    print_info "Por favor, especifica el nombre de la base de datos:"
    read -p "Nombre de la base de datos: " TEST_DB
fi

if [ -z "$TEST_DB" ]; then
    print_error "No se especificó base de datos"
    exit 1
fi

print_info "Base de datos a usar: $TEST_DB"

# 12. Instalar el módulo
print_info "=========================================="
print_info "Instalando módulo mcp_server..."
print_info "=========================================="

# Detener Odoo si está corriendo
print_info "Verificando si Odoo está corriendo..."
if $SUDO systemctl is-active --quiet odoo 2>/dev/null; then
    print_warn "Odoo está corriendo. Se detendrá temporalmente..."
    $SUDO systemctl stop odoo
    ODOO_WAS_RUNNING=true
else
    ODOO_WAS_RUNNING=false
fi

# Instalar el módulo
print_info "Ejecutando instalación del módulo..."
INSTALL_CMD="$SUDO -u $ODOO_USER $ODOO_BIN -c $ODOO_CONFIG -d $TEST_DB -i mcp_server --stop-after-init"

print_info "Comando: $INSTALL_CMD"
echo ""

# Ejecutar instalación y capturar output
if $INSTALL_CMD 2>&1 | tee /tmp/odoo_install.log; then
    print_info "=========================================="
    print_info "✓ Instalación completada exitosamente"
    print_info "=========================================="
    
    # Verificar si hay errores en el log
    if grep -i "error\|exception\|traceback" /tmp/odoo_install.log | grep -v "INFO\|DEBUG"; then
        print_warn "Se encontraron algunos errores en el log. Revisa /tmp/odoo_install.log"
    fi
    
    # Reiniciar Odoo si estaba corriendo
    if [ "$ODOO_WAS_RUNNING" = true ]; then
        print_info "Reiniciando servicio de Odoo..."
        $SUDO systemctl start odoo
        sleep 2
        if $SUDO systemctl is-active --quiet odoo; then
            print_info "✓ Odoo reiniciado correctamente"
        else
            print_error "Error al reiniciar Odoo. Revisa los logs:"
            print_info "  sudo journalctl -u odoo -n 50"
        fi
    fi
    
    print_info ""
    print_info "=========================================="
    print_info "Instalación completada"
    print_info "=========================================="
    print_info "Módulo instalado en: $INSTALL_DIR/mcp_server"
    print_info "Base de datos: $TEST_DB"
    print_info "Log de instalación: /tmp/odoo_install.log"
    print_info ""
    print_info "Para verificar la instalación:"
    print_info "  1. Accede a la interfaz web de Odoo"
    print_info "  2. Ve a Apps > MCP Server"
    print_info "  3. Verifica que el módulo esté instalado"
    
else
    print_error "=========================================="
    print_error "Error durante la instalación"
    print_error "=========================================="
    print_error "Revisa el log en: /tmp/odoo_install.log"
    print_info ""
    print_info "Últimas líneas del log:"
    tail -30 /tmp/odoo_install.log
    
    # Reiniciar Odoo si estaba corriendo
    if [ "$ODOO_WAS_RUNNING" = true ]; then
        print_info "Reiniciando servicio de Odoo..."
        $SUDO systemctl start odoo
    fi
    
    exit 1
fi

