output "resource_group_name" {
  value = azurerm_resource_group.meridian.name
}

output "storage_account_name" {
  value = module.storage.storage_account_name
}

output "adls_primary_dfs_endpoint" {
  value = module.storage.primary_dfs_endpoint
}

output "key_vault_uri" {
  value = module.iam.key_vault_uri
}

output "identity_client_id" {
  value = module.iam.identity_client_id
}

output "adf_name" {
  value = module.adf.adf_name
}

output "container_app_env_id" {
  value = module.compute.container_app_env_id
}