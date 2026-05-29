# Natiah deployment (Ubuntu VPS)

## Prereqs
- Ubuntu 22.04+ VPS
- A domain (A/AAAA record) pointing to the server IP
- SSH access

## 1) Install Docker, Docker Compose, Nginx, Certbot
On the VPS:

```bash
sudo bash /opt/natiah/docker/deploy/ubuntu_setup.sh
```

If your repo is not yet on the server, copy the scripts first or clone the repo and run:

```bash
sudo bash docker/deploy/ubuntu_setup.sh
```

## 2) Configure environment
Copy the example env file and update secrets:

```bash
cp docker/.env.prod.example docker/.env.prod
nano docker/.env.prod
```

Minimum variables to change:
- `POSTGRES_PASSWORD`
- `DATABASE_URL` (must match the password above)
- `JWT_SECRET`
- `CORS_ORIGINS`
- `NEXT_PUBLIC_API_URL`

## 3) Deploy containers (prod compose)
If you deploy from git:

```bash
sudo REPO_URL=https://github.com/YOUR_ORG/Natiah.git BRANCH=main bash docker/deploy/app_deploy.sh
```

Or if the repo is already in place (e.g. `/opt/natiah`):

```bash
sudo docker compose --env-file docker/.env.prod -f docker/docker-compose.yml -f docker/docker-compose.prod.yml up -d --build
```

## 4) Nginx + SSL (Let’s Encrypt)
Run:

```bash
sudo bash docker/deploy/nginx_ssl.sh YOUR_DOMAIN
```

Nginx routes:
- `https://YOUR_DOMAIN/` → frontend (localhost:3000)
- `https://YOUR_DOMAIN/api/...` → backend (localhost:8000)

## 5) Auto-restart
Two layers are used:
- Container auto-restart via `restart: unless-stopped` in prod compose override
- Optional systemd unit to ensure the stack is brought up after reboot

Install the systemd unit (optional):

```bash
sudo mkdir -p /opt/natiah
sudo cp docker/deploy/systemd_natiah_compose.service /etc/systemd/system/natiah.service
sudo systemctl daemon-reload
sudo systemctl enable natiah.service
sudo systemctl start natiah.service
```

## PM2 (optional)
If you ever run the frontend outside Docker:

```bash
sudo npm i -g pm2
cd frontend
pm2 start "npm run start -- -p 3000" --name natiah-frontend
pm2 save
pm2 startup
```
