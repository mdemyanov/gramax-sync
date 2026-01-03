#!/bin/bash
# Скрипт для получения Application ID OAuth приложения gramax-sync из GitLab

GITLAB_URL="${1:-https://itsmf.gitlab.yandexcloud.net}"
APP_NAME="${2:-gramax-sync}"

echo "🔍 Поиск OAuth Application '$APP_NAME' в GitLab..."
echo "📍 URL: $GITLAB_URL"
echo ""
echo "📋 Инструкция:"
echo "1. Откройте в браузере: $GITLAB_URL/-/profile/applications"
echo "2. Найдите приложение '$APP_NAME'"
echo "3. Скопируйте Application ID (это длинная строка)"
echo ""
echo "💡 После получения Application ID выполните:"
echo "   export GRAMAX_OAUTH_APPLICATION_ID=\"ваш_application_id\""
echo ""
echo "🔐 Если у вас есть Application Secret (для Confidential Application):"
echo "   export GRAMAX_OAUTH_APPLICATION_SECRET=\"ваш_secret\""
echo ""
echo "✅ Затем запустите тесты:"
echo "   pytest tests/"

