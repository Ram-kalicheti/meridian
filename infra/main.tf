terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.110"
    }
  }
  required_version = ">= 1.7"
}

provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy    = true
      recover_soft_deleted_key_vaults = false
    }
  }
  subscription_id = var.subscription_id
}

data "azurerm_client_config" "current" {}

resource "azurerm_resource_group" "meridian" {
  name     = var.resource_group_name
  location = var.location
}

module "storage" {
  source               = "./modules/storage"
  resource_group_name  = azurerm_resource_group.meridian.name
  location             = azurerm_resource_group.meridian.location
  storage_account_name = var.storage_account_name
}

resource "azurerm_log_analytics_workspace" "meridian" {
  name                = "meridian-logs"
  resource_group_name = azurerm_resource_group.meridian.name
  location            = azurerm_resource_group.meridian.location
  sku                 = "PerGB2018"
  retention_in_days   = 30
}

module "iam" {
  source              = "./modules/iam"
  resource_group_name = azurerm_resource_group.meridian.name
  location            = azurerm_resource_group.meridian.location
  key_vault_name      = var.key_vault_name
  identity_name       = var.identity_name
  tenant_id           = data.azurerm_client_config.current.tenant_id
  storage_account_id  = module.storage.storage_account_id
}

module "adf" {
  source              = "./modules/adf"
  resource_group_name = azurerm_resource_group.meridian.name
  location            = azurerm_resource_group.meridian.location
  adf_name            = var.adf_name
  identity_id         = module.iam.identity_id
}

module "compute" {
  source                      = "./modules/compute"
  resource_group_name         = azurerm_resource_group.meridian.name
  location                    = azurerm_resource_group.meridian.location
  container_app_env_name      = var.container_app_env_name
  log_analytics_workspace_id  = azurerm_log_analytics_workspace.meridian.id
  log_analytics_workspace_key = azurerm_log_analytics_workspace.meridian.primary_shared_key
}
