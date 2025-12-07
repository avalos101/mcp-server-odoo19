# Changelog

All notable changes to the MCP Server Odoo module will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [19.0.1.0.0] - 2025-01-XX

### Changed
- **Migration to Odoo 19**: Migrated module from Odoo 18.0 to Odoo 19.0
- **Version Update**: Updated module version to 19.0.1.0.0
- **Documentation**: Updated README and documentation references to Odoo 19.0

### Technical Details
- Compatible with Odoo 19.0
- All existing functionality preserved
- No breaking changes in API or configuration

## [18.0.1.0.2] - 2025-06-28

### Fixed
- **Configuration Defaults**: Fixed checkbox states in settings view to properly reflect field defaults

## [18.0.1.0.1] - 2025-06-16

### Fixed
- **XML-RPC Date Marshaling**: Fixed "cannot marshal objects" error by using Odoo's custom XML-RPC marshaller for proper date/datetime serialization

### Changed
- **Development Mode Logging**: Enabled logging in development mode for better debugging

## [18.0.1.0.0] - 2025-06-10

### Added

- **Security Groups**: MCP Administrator (full access) and MCP User (read-only)
- **Model Configuration**: Enable/disable models with granular permissions (read, write, create, unlink)
- **API Key Authentication**: Secure authentication with rate limiting support
- **REST API Endpoints**:
  - `/mcp/health` - Health check
  - `/mcp/auth/validate` - API key validation
  - `/mcp/system/info` - System information
  - `/mcp/models` - List enabled models
  - `/mcp/models/{model}/access` - Check permissions
- **XML-RPC Controllers**: MCP-specific endpoints with access control
  - `/mcp/xmlrpc/common` - Authentication
  - `/mcp/xmlrpc/object` - Model operations
- **Configuration UI**: Settings integration and model selection wizard
- **Audit Logging**: Comprehensive operation tracking with built-in viewer
- **Data Models**:
  - `mcp.enabled.model` - Model access configuration
  - `mcp.log` - Audit trail

### Technical Details
- Compatible with Odoo 18.0
- Follows Odoo module best practices
- Extensive test coverage
- Full documentation and type hints