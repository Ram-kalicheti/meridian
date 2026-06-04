variable "resource_group_name" {
  type = string
}

variable "location" {
  type = string
}

variable "adf_name" {
  type = string
}

variable "identity_id" {
  type        = string
  description = "User-assigned managed identity ID to attach to ADF"
}