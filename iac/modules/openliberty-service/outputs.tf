output "container_name" {
  description = "容器名稱"
  value       = docker_container.this.name
}

output "url" {
  description = "服務本機存取位址(僅綁 127.0.0.1)"
  value       = "http://127.0.0.1:${var.http_port}"
}
