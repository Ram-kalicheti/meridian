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
