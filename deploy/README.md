# Деплой на VPS

## 1. Сервер

Timeweb Cloud (или любой другой), Ubuntu 22.04+, от 2 ГБ RAM. Привязать домен (A-запись на IP сервера).

```bash
# на сервере, от root
apt update && apt upgrade -y
apt install -y docker.io docker-compose-plugin fail2ban ufw git

ufw allow 22
ufw allow 80
ufw allow 443
ufw --force enable

systemctl enable --now fail2ban
```

SSH — только по ключу (отключить пароль в `/etc/ssh/sshd_config`: `PasswordAuthentication no`, затем `systemctl restart sshd`).

## 2. Код и конфиг

```bash
git clone https://github.com/MyNameIsMoran14/JVI.git med-helper
cd med-helper
cp .env.example .env
nano .env   # заполнить все ключи, DOMAIN=ваш-домен, MINI_APP_URL=https://ваш-домен
```

## 3. Запуск

```bash
docker compose -f deploy/docker-compose.yml up -d --build
docker compose -f deploy/docker-compose.yml exec api python -m app.extraction.seed
```

Caddy сам получит сертификат Let's Encrypt для `DOMAIN` при первом запросе — подождать пару минут после первого `docker compose up`.

## 4. Проверка

```bash
curl https://ваш-домен/health
```

Открыть бота в Telegram → `/start` → кнопка «Открыть панель» должна вести на `https://ваш-домен`.

## 5. Бэкапы (пока вручную, автоматизация — этап 5 плана)

```bash
docker compose -f deploy/docker-compose.yml exec -T postgres pg_dump -U med med > backup_$(date +%F).sql
```
