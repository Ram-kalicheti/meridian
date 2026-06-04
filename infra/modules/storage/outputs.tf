output "storage_account_name" {
  value = azurerm_storage_account.adls.name
}

output "storage_account_id" {
  value = azurerm_storage_account.adls.id
}

output "primary_dfs_endpoint" {
  value = azurerm_storage_account.adls.primary_dfs_endpoint
}
