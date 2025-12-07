# Instrucciones para Probar el Módulo en Google Cloud con Odoo 19

## Prerrequisitos

- Cuenta de Google Cloud Platform (GCP) activa
- Proyecto de GCP creado
- Conocimientos básicos de Linux y Odoo

## Paso 1: Crear una Instancia de VM en Google Cloud

### Opción A: Usando la Consola Web

1. Ve a [Google Cloud Console](https://console.cloud.google.com/)
2. Selecciona tu proyecto
3. Navega a **Compute Engine > VM instances**
4. Haz clic en **"Create Instance"**
5. Configura la instancia:
   - **Name**: `odoo19-mcp-server`
   - **Machine type**: `e2-medium` (2 vCPU, 4 GB RAM) como mínimo
   - **Boot disk**: 
     - **OS**: Ubuntu 22.04 LTS
     - **Disk size**: 20 GB mínimo
   - **Firewall**: Marca "Allow HTTP traffic" y "Allow HTTPS traffic"
6. Haz clic en **"Create"**

### Opción B: Usando gcloud CLI

```bash
gcloud compute instances create odoo19-mcp-server \
    --zone=us-central1-a \
    --machine-type=e2-medium \
    --image-family=ubuntu-2204-lts \
    --image-project=ubuntu-os-cloud \
    --boot-disk-size=20GB \
    --tags=http-server,https-server
```

## Paso 2: Conectarse a la Instancia

```bash
# Obtener la IP externa
gcloud compute instances describe odoo19-mcp-server \
    --zone=us-central1-a \
    --format='get(networkInterfaces[0].accessConfigs[0].natIP)'

# Conectarse por SSH
gcloud compute ssh odoo19-mcp-server --zone=us-central1-a
```

## Paso 3: Instalar Odoo 19 en la Instancia

Una vez conectado a la instancia, ejecuta:

```bash
# Actualizar el sistema
sudo apt update && sudo apt upgrade -y

# Instalar dependencias
sudo apt install -y python3-pip python3-dev python3-venv \
    libxml2-dev libxslt1-dev libevent-dev libsasl2-dev \
    libldap2-dev build-essential libssl-dev libffi-dev \
    libmysqlclient-dev libjpeg-dev libpq-dev libjpeg8-dev \
    zlib1g-dev wget git postgresql postgresql-contrib \
    nginx supervisor

# Crear usuario para Odoo
sudo useradd -m -d /opt/odoo -s /bin/bash odoo

# Crear directorio para Odoo
sudo mkdir -p /opt/odoo
sudo chown odoo:odoo /opt/odoo

# Cambiar al usuario odoo
sudo su - odoo

# Descargar Odoo 19
cd /opt/odoo
wget https://nightly.odoo.com/19.0/nightly/src/odoo_19.0.latest.tar.gz
tar -xzf odoo_19.0.latest.tar.gz
mv odoo-19.0* odoo
cd odoo

# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias de Python
pip install --upgrade pip
pip install -r requirements.txt

# Crear directorio para addons personalizados
mkdir -p /opt/odoo/custom-addons
```

## Paso 4: Instalar el Módulo MCP Server

```bash
# Como usuario odoo
cd /opt/odoo/custom-addons

# Clonar el repositorio (reemplaza con tu URL de GitHub)
git clone https://github.com/USERNAME/mcp-server-odoo19.git
# O si prefieres copiar el módulo directamente:
# scp -r /ruta/local/mcp_server user@IP:/opt/odoo/custom-addons/

# Verificar que el módulo esté en el lugar correcto
ls -la /opt/odoo/custom-addons/mcp_server
```

## Paso 5: Configurar Odoo

```bash
# Crear archivo de configuración
sudo nano /etc/odoo.conf
```

Agrega el siguiente contenido:

```ini
[options]
; This is the password that allows database operations:
admin_passwd = admin
db_host = False
db_port = False
db_user = odoo
db_password = False
addons_path = /opt/odoo/odoo/addons,/opt/odoo/custom-addons
xmlrpc_port = 8069
logfile = /var/log/odoo/odoo-server.log
log_level = info
```

```bash
# Crear directorio de logs
sudo mkdir -p /var/log/odoo
sudo chown odoo:odoo /var/log/odoo

# Crear base de datos
sudo -u postgres createuser -s odoo
sudo -u postgres createdb odoo19_test -O odoo
```

## Paso 6: Iniciar Odoo

```bash
# Como usuario odoo
cd /opt/odoo/odoo
source venv/bin/activate
./odoo-bin -c /etc/odoo.conf -d odoo19_test --init base
```

## Paso 7: Instalar el Módulo MCP Server

1. Abre tu navegador y ve a: `http://TU_IP_EXTERNA:8069`
2. Crea una base de datos nueva o usa la existente
3. Ve a **Apps** > **Update Apps List**
4. Busca "MCP Server"
5. Haz clic en **Install**

## Paso 8: Configurar el Módulo

1. Ve a **Settings > MCP Server**
2. Habilita "Enable MCP Access"
3. Haz clic en "Manage MCP Available Models"
4. Agrega los modelos que quieras exponer (ej: `res.partner`, `product.product`)
5. Configura los permisos para cada modelo
6. Ve a **Settings > Users & Companies > Users**
7. Selecciona un usuario y genera una API Key en la pestaña "API Keys"

## Paso 9: Probar el Módulo

### Probar el endpoint de health:

```bash
curl http://TU_IP_EXTERNA:8069/mcp/health
```

Deberías recibir una respuesta JSON con `"status": "ok"`

### Probar la validación de API Key:

```bash
curl -X GET http://TU_IP_EXTERNA:8069/mcp/auth/validate \
  -H "X-API-Key: TU_API_KEY_AQUI"
```

### Probar listado de modelos:

```bash
curl http://TU_IP_EXTERNA:8069/mcp/models \
  -H "X-API-Key: TU_API_KEY_AQUI"
```

## Paso 10: Configurar Nginx (Opcional pero Recomendado)

Para producción, configura Nginx como proxy reverso:

```bash
sudo nano /etc/nginx/sites-available/odoo
```

Agrega:

```nginx
upstream odoo {
    server 127.0.0.1:8069;
}

server {
    listen 80;
    server_name TU_DOMINIO_O_IP;

    client_max_body_size 50M;

    location / {
        proxy_pass http://odoo;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/odoo /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## Paso 11: Configurar Supervisor (Para Ejecutar Odoo como Servicio)

```bash
sudo nano /etc/supervisor/conf.d/odoo.conf
```

Agrega:

```ini
[program:odoo]
command=/opt/odoo/odoo/venv/bin/python3 /opt/odoo/odoo/odoo-bin -c /etc/odoo.conf
directory=/opt/odoo/odoo
user=odoo
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/odoo/odoo-server.log
```

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start odoo
```

## Solución de Problemas

### El módulo no aparece en Apps
- Verifica que el módulo esté en `/opt/odoo/custom-addons/mcp_server`
- Verifica que `addons_path` en `/etc/odoo.conf` incluya `/opt/odoo/custom-addons`
- Actualiza la lista de apps: **Apps > Update Apps List**

### Error de permisos
```bash
sudo chown -R odoo:odoo /opt/odoo/custom-addons/mcp_server
```

### Error de conexión a la base de datos
```bash
sudo -u postgres psql
ALTER USER odoo WITH PASSWORD 'tu_password';
```

### Ver logs de Odoo
```bash
sudo tail -f /var/log/odoo/odoo-server.log
```

## Seguridad

- Cambia la contraseña de admin en `/etc/odoo.conf`
- Configura HTTPS usando Let's Encrypt
- Configura firewall para limitar acceso
- Usa API keys en lugar de usuario/contraseña
- Revisa regularmente los logs de MCP en Odoo

## Costos Estimados

- **e2-medium**: ~$25-30 USD/mes
- **e2-standard-2**: ~$50-60 USD/mes (recomendado para producción)
- **Storage**: ~$0.10 USD/GB/mes

## Limpieza

Para eliminar la instancia cuando termines las pruebas:

```bash
gcloud compute instances delete odoo19-mcp-server --zone=us-central1-a
```

