output "identity_id" {
  value = azurerm_user_assigned_identity.meridian.id
}

output "identity_principal_id" {
  value = azurerm_user_assigned_identity.meridian.principal_id
}

output "identity_client_id" {
  value = azurerm_user_assigned_identity.meridian.client_id
}

output "key_vault_id" {
  value = azurerm_key_vault.meridian.id
}

output "key_vault_uri" {
  value = azurerm_key_vault.meridian.vault_uri
}