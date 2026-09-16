terraform {
  backend "oss" {}
  required_providers {
    alicloud = { source = "aliyun/alicloud", version = "~> 1.279" }
    archive  = { source = "hashicorp/archive", version = "~> 2.0" }
  }
}

variable "region" {
  type = string
  default = "cn-hangzhou"
}
variable "project_name" {
  type = string
  default = "inventory-platform"
}
variable "tenant_keys_json" {
  type = string
  sensitive = true
}
variable "runtime_access_key" {
  type = string
  sensitive = true
}
variable "runtime_access_secret" {
  type = string
  sensitive = true
}
provider "alicloud" { region = var.region }

data "archive_file" "platform" {
  type = "zip"
  source_dir = "${path.module}/../dist/package"
  output_path = "${path.module}/../dist/alicloud-platform.zip"
}

# The FC provider uses CRC64 (not SHA-256) to detect code updates.
data "alicloud_file_crc64_checksum" "platform" {
  filename = data.archive_file.platform.output_path
}

resource "alicloud_ots_instance" "inventory" {
  # Tablestore instance names are limited to 16 bytes.
  name = "invplatots"
  description = "Multi tenant inventory platform"
  accessed_by = "Any"
}
resource "alicloud_ots_table" "inventory" {
  instance_name = alicloud_ots_instance.inventory.name
  table_name = "inventory"
  time_to_live = -1
  max_version = 1
  primary_key {
    name = "PK"
    type = "String"
  }
  primary_key {
    name = "SK"
    type = "String"
  }
}
resource "alicloud_ram_role" "fc" {
  name = "${var.project_name}-fc-role"
  document = jsonencode({ Version = "1", Statement = [{ Action = "sts:AssumeRole", Effect = "Allow", Principal = { Service = ["fc.aliyuncs.com"] } }] })
  description = "Runtime role for inventory platform FC functions"
  force = true
}
resource "alicloud_ram_role_policy_attachment" "fc_log" {
  role_name = alicloud_ram_role.fc.name
  policy_name = "AliyunLogFullAccess"
  policy_type = "System"
}
resource "alicloud_ram_role_policy_attachment" "fc_ots" {
  role_name = alicloud_ram_role.fc.name
  policy_name = "AliyunOTSFullAccess"
  policy_type = "System"
}
locals {
  environment = {
    TENANT_KEYS = var.tenant_keys_json
    ALIBABA_CLOUD_ACCESS_KEY_ID = var.runtime_access_key
    ALIBABA_CLOUD_ACCESS_KEY_SECRET = var.runtime_access_secret
    OTS_INSTANCE = alicloud_ots_instance.inventory.name
    OTS_TABLE = alicloud_ots_table.inventory.table_name
    OTS_ENDPOINT = "https://${alicloud_ots_instance.inventory.name}.${var.region}.ots.aliyuncs.com"
  }
}

resource "alicloud_fc_service" "platform" {
  name = var.project_name
  role = alicloud_ram_role.fc.arn
  description = "Inventory event platform"
}
resource "alicloud_fc_function" "api" {
  service = alicloud_fc_service.platform.name
  name = "inventory-api"
  description = "Public inventory API"
  filename = data.archive_file.platform.output_path
  # The filename is stable across CI runs.  This checksum makes Terraform
  # upload a new function revision whenever the packaged source changes.
  code_checksum = data.alicloud_file_crc64_checksum.platform.checksum
  memory_size = "512"
  runtime = "python3.10"
  handler = "app.alicloud_handlers.http_handler"
  environment_variables = local.environment
}
resource "alicloud_fc_trigger" "api_http" {
  service = alicloud_fc_service.platform.name
  function = alicloud_fc_function.api.name
  name = "http"
  type = "http"
  config = jsonencode({ authType = "anonymous", methods = ["GET", "POST", "OPTIONS"] })
}
output "deploy_note" { value = "Retrieve the FC HTTP trigger URL from the FC console after apply." }
