resource "azurerm_container_app_environment" "meridian" {
  name                       = var.container_app_env_name
  resource_group_name        = var.resource_group_name
  location                   = var.location
  log_analytics_workspace_id = var.log_analytics_workspace_id

  tags = {
    project = "meridian"
    layer   = "compute"
  }
}