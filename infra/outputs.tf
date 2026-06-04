output "resource_group_name" {
  value = azurerm_resource_group.meridian.name
}

output "storage_account_name" {
  value = module.storage.storage_account_name
}

output "adls_primary_dfs_endpoint" {
  value = module.storage.primary_dfs_endpoint
}
