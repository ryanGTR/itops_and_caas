# vm-openliberty — itops 的「真 VM」部署目標

itops 用 **OpenTofu** 開一台 **QEMU/libvirt Linux VM**,在其上跑 **OpenLiberty** 部署 app,
前面掛 itops 的部署前驗章閘門。是 D6 podman 容器部署的 VM 升級版(更貼近銀行「部署到主機」的現實)。

## 怎麼跑

```bash
# 一鍵:閘門 → tofu apply 開 VM → 部署 OpenLiberty → 煙霧測試
scripts/deploy_openliberty_vm.sh
# 收掉
tofu -chdir=iac/environments/vm-openliberty destroy -auto-approve
```

## 架構

- `versions.tf` — `qemu:///system` + default NAT 網路(VM 取得 192.168.122.x,host 直連 app)。
- `main.tf` — base(Debian 12 cloud image)→ overlay 系統碟 → cloud-init(Java/agent)→ domain。
- `cloud_init.cfg` — 開機自動裝 qemu-guest-agent、設存取。
- `provision-app.sh` — [VM 內] 裝 Java 21 + OpenLiberty + 部署 WAR(由 host scp 推入)。

## 前置

- libvirt(`qemu:///system`,`default` NAT 網路 active)、OpenTofu、`sshpass`、`cdrtools`(提供 mkisofs)。
- Debian 12 cloud image 放 `~/itops-vm/images/debian12-base.qcow2`(不入版控,太大)。
- dmacvicar/libvirt provider **釘 0.7.6**(0.8+ 改低階 XML API,不相容本設定)。

## 真 live 踩過的雷(都已解,記給後人)

1. **btrfs qcow2 雙重 CoW 卡死**(=k8s-lab lessons #9 同款):映像目錄 `chattr +C`(No_COW);輕量單 VM 其實不觸發,重負載才需要。
2. **dmacvicar provider 0.9.x** 是低階 XML 映射 API(無 disk/network_interface/cloudinit)→ 釘 **0.7.6** 經典 API。
3. **缺 mkisofs**(cloudinit ISO 要用)→ `pacman -S cdrtools`。
4. **qemu:///session 在此機 daemon 佈局不順**(modular socket 缺、provider 落到 system 建 root 檔)→ 改 **qemu:///system + default pool**(root 讀家目錄 base image、vol 放 libvirt-qemu 可讀處)。
5. **VM→host TCP 被擋**(libvirt 預設只放行 DNS/DHCP)→ 推檔改 **SSH/scp host→VM**(正常方向可通)。
6. **zsh 不對未引用變數分詞** → ssh `-o` 旗標要 inline(別塞進變數)。
7. **WAR 由 Java 21 編譯、VM 預設 Java 17**(`UnsupportedClassVersionError` class 65 vs 61)→ 裝 **Temurin 21**,設 `JAVA_HOME`。
