terraform {
  required_version = ">= 1.6"
  required_providers {
    # 用 Docker provider 對接 rootless Podman 的 Docker 相容 socket。
    # 目前無成熟的官方 OpenTofu Podman provider,docker provider 指向 podman.sock
    # 是務實且常見的做法(見 docs/adr/0002)。
    docker = {
      source  = "kreuzwerker/docker"
      version = ">= 3.0"
    }
  }
}
