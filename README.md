# Cloudflare DNS Panel (Streamlit)

一个基于 **Streamlit** 的 Cloudflare DNS 管理面板，支持通过 Web 界面快速管理 Cloudflare 域名 DNS 记录，适合部署在 Docker / 云服务器上使用。

---

## ✨ 功能特点

- 🌐 Web 可视化管理 Cloudflare DNS
- ⚡ 基于 Streamlit，轻量快速
- 🐳 支持 Docker 一键部署
- 🔐 使用 Cloudflare API Token，安全可靠
- 📱 浏览器即可访问，无需额外客户端

---

## 🚀 快速开始（Docker）

### 1️⃣ 拉取并运行容器

```bash
docker run -d --name cfpanel \
  --restart unless-stopped \
  -p 8000:8000 \
  wuyouxing/streamlit-cloudflare-dns:latest
