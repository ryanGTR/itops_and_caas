#!/usr/bin/env bash
# provision-app.sh — [在 VM 內以 root 跑] 裝 Java 21 + OpenLiberty + 部署 app WAR + 啟動。
# 由 host 端 scripts/deploy_openliberty_vm.sh 透過 SSH 推進來執行。
#
# 前置:/tmp/liberty-backend.war 與 /tmp/server.xml 已由 host scp 進來。
# 對應 D6「部署到 OpenLiberty」的 VM 版(podman 版見 scripts/deploy_openliberty.sh)。
set -euo pipefail

OLVER="${OLVER:-24.0.0.12}"
WLP=/opt/wlp
SRV="$WLP/usr/servers/defaultServer"
export DEBIAN_FRONTEND=noninteractive

# Java 21:WAR 由 Java 21 編譯(class 65),VM 預設 Java 17 載不動 → 裝 Temurin 21。
if [ ! -x /opt/jdk21/bin/java ]; then
  curl -sSL -o /tmp/jre21.tgz "https://api.adoptium.net/v3/binary/latest/21/ga/linux/x64/jre/hotspot/normal/eclipse"
  mkdir -p /opt/jdk21 && tar -xzf /tmp/jre21.tgz -C /opt/jdk21 --strip-components=1
fi

# OpenLiberty 全功能 runtime(含 jakarta + microprofile features)
apt-get -qq install -y unzip >/dev/null 2>&1 || true
if [ ! -d "$WLP" ]; then
  curl -sSL -o /tmp/ol.zip "https://repo1.maven.org/maven2/io/openliberty/openliberty-runtime/$OLVER/openliberty-runtime-$OLVER.zip"
  unzip -q -o /tmp/ol.zip -d /opt
fi
[ -d "$SRV" ] || "$WLP/bin/server" create defaultServer

# 部署 app:server.xml(host="*" 對外)+ WAR
cp /tmp/server.xml "$SRV/server.xml"
mkdir -p "$SRV/apps"
cp /tmp/liberty-backend.war "$SRV/apps/liberty-backend.war"
echo "JAVA_HOME=/opt/jdk21" > "$SRV/server.env"

"$WLP/bin/server" stop defaultServer 2>/dev/null || true
JAVA_HOME=/opt/jdk21 "$WLP/bin/server" start defaultServer
echo "PROVISION_DONE"
