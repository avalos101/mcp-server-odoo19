# Instrucciones para Configurar el Repositorio en GitHub

## Paso 1: Crear el Repositorio en GitHub

1. Ve a [GitHub](https://github.com) e inicia sesión en tu cuenta
2. Haz clic en el botón "+" en la esquina superior derecha y selecciona "New repository"
3. Configura el repositorio:
   - **Name**: `mcp-server-odoo19` (o el nombre que prefieras)
   - **Description**: "MCP Server module for Odoo 19 - Migrated from Odoo 18"
   - **Visibility**: Elige Público o Privado según tus preferencias
   - **NO marques** "Initialize this repository with a README" (ya tenemos uno)
   - **NO agregues** .gitignore ni licencia (ya los tenemos)
4. Haz clic en "Create repository"

## Paso 2: Conectar el Repositorio Local con GitHub

Una vez creado el repositorio en GitHub, ejecuta los siguientes comandos en tu terminal:

```bash
cd "/Users/diegoavalos/Documents/proyecto migracion mcp to odoov19"

# Agregar el remoto (reemplaza USERNAME con tu usuario de GitHub)
git remote add origin https://github.com/USERNAME/mcp-server-odoo19.git

# O si prefieres usar SSH:
# git remote add origin git@github.com:USERNAME/mcp-server-odoo19.git

# Verificar que el remoto se agregó correctamente
git remote -v

# Cambiar a la rama main si es necesario (GitHub usa 'main' por defecto)
git branch -M main

# Subir el código a GitHub
git push -u origin main
```

## Paso 3: Verificar la Sincronización

1. Ve a tu repositorio en GitHub
2. Verifica que todos los archivos estén presentes
3. El README.md debería mostrarse automáticamente en la página principal

## Comandos Útiles para el Futuro

### Subir cambios nuevos:
```bash
git add .
git commit -m "Descripción de los cambios"
git push origin main
```

### Crear una nueva rama para desarrollo:
```bash
git checkout -b develop
git push -u origin develop
```

### Sincronizar cambios desde GitHub:
```bash
git pull origin main
```

## Notas

- Si GitHub te pide autenticación, puedes usar:
  - **Personal Access Token** (recomendado): Ve a Settings > Developer settings > Personal access tokens
  - **SSH Keys**: Configura SSH keys en Settings > SSH and GPG keys

