# itops VM 部署目標(spike)— 用 OpenTofu 開 QEMU/libvirt Linux VM。
# qemu:///system + default pool + default NAT 網路。base image 由 root 從家目錄複製進 default pool。

# 基底:Debian 12 cloud image(已下載到家目錄;system libvirtd 以 root 讀得到)
resource "libvirt_volume" "base" {
  name   = "itops-debian12-base.qcow2"
  pool   = "default"
  source = "/home/ryan/itops-vm/images/debian12-base.qcow2"
  format = "qcow2"
}

# VM 系統碟:以 base 為 backing 的 overlay
resource "libvirt_volume" "os" {
  name           = "itops-ol-vm.qcow2"
  pool           = "default"
  base_volume_id = libvirt_volume.base.id
  size           = 8589934592 # 8 GiB
  format         = "qcow2"
}

resource "libvirt_cloudinit_disk" "ci" {
  name      = "itops-ol-vm-cidata.iso"
  pool      = "default"
  user_data = file("${path.module}/cloud_init.cfg")
}

resource "libvirt_domain" "vm" {
  name       = "itops-ol-vm"
  memory     = 1024
  vcpu       = 2
  cloudinit  = libvirt_cloudinit_disk.ci.id
  qemu_agent = true

  network_interface {
    network_name   = "default" # libvirt 預設 NAT;VM 取得 192.168.122.x
    wait_for_lease = true      # apply 等到拿到 DHCP IP
  }

  disk {
    volume_id = libvirt_volume.os.id
  }

  console {
    type        = "pty"
    target_port = "0"
    target_type = "serial"
  }
}

output "vm_name" {
  value = libvirt_domain.vm.name
}

output "vm_ip" {
  value = try(libvirt_domain.vm.network_interface[0].addresses[0], "(pending)")
}
