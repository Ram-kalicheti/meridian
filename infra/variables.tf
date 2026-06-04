variable "subscription_id" {
  description = "Azure subscription ID"
  type        = string
}

variable "location" {
  type    = string
  default = "eastus"
}

variable "resource_group_name" {
  type    = string
  default = "meridian-rg"
}

variable "storage_account_name" {
  description = "ADLS Gen2 account name — globally unique, lowercase, no hyphens, max 24 chars"
  type        = string
  default     = "meridianstgrk1"
}

variable "key_vault_name" {
  description = "Key Vault name — globally unique, 3-24 chars"
  type        = string
  default     = "meridian-kv-rk1"
}

variable "adf_name" {
  type    = string
  default = "meridian-adf"
}

variable "container_app_env_name" {
  type    = string
  default = "meridian-cae"
}

variable "identity_name" {
  type    = string
  default = "meridian-identity"
}
