terraform {
  required_version = ">= 1.6"
  required_providers {
    libvirt = {
      source  = "dmacvicar/libvirt"
      version = "0.7.6" # 經典友善 API(disk/network_interface/cloudinit);0.8+ 改低階 XML 映射
    }
  }
}
# qemu:///system:用 default NAT 網路(virbr0),VM 取得可達 IP(192.168.122.x),host 直連 app。
# vol 放 libvirt default pool(/var/lib/libvirt/images),libvirt-qemu 可讀;免 sudo(libvirt 群組+polkit)。
provider "libvirt" {
  uri = "qemu:///system"
}
