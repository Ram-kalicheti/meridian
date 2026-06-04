resource "azurerm_data_factory" "meridian" {
  name                = var.adf_name
  resource_group_name = var.resource_group_name
  location            = var.location

  identity {
    type         = "UserAssigned"
    identity_ids = [var.identity_id]
  }

  tags = {
    project = "meridian"
    layer   = "orchestration"
  }
}