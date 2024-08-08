variable "node_pools" {}
variable "project_id" {}
variable "resource_prefix" {}
variable "region" {}
variable "user_workload_path" {
  default = "./sample-tcpx-workload/sample-job.yaml"
}

module "a3-gke" {
  source = "../../terraform/modules/cluster/gke"#github.com/GoogleCloudPlatform/ai-infra-cluster-provisioning//a3/terraform/modules/cluster/gke"

  node_pools         = var.node_pools
  project_id         = var.project_id
  resource_prefix    = var.resource_prefix
  region             = var.region
  user_workload_path = var.user_workload_path
}
