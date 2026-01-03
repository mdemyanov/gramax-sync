#!/bin/bash
# Скрипт для проверки конфигурации OAuth

echo "🔍 Проверка конфигурации OAuth для gramax-sync"
echo "=============================================="
echo ""

GITLAB_URL="${TEST_GITLAB_URL:-https://itsmf.gitlab.yandexcloud.net}"
APP_ID="${GRAMAX_OAUTH_APPLICATION_ID:-}"
APP_SECRET="${GRAMAX_OAUTH_APPLICATION_SECRET:-}"

echo "📍 GitLab URL: $GITLAB_URL"
echo ""

if [ -z "$APP_ID" ]; then
    echo "❌ GRAMAX_OAUTH_APPLICATION_ID: НЕ УСТАНОВЛЕН"
    echo ""
    echo "⚠️  ВАЖНО: Тесты требуют установки реального Application ID!"
    echo "   Тестовое значение 'test_app_id' больше не используется."
    echo ""
    echo "💡 Решение:"
    echo "   1. Создайте OAuth Application в GitLab:"
    echo "      $GITLAB_URL/-/profile/applications"
    echo "   2. Установите Application ID:"
    echo "      export GRAMAX_OAUTH_APPLICATION_ID=\"ваш_id\""
    echo "   3. Или используйте автоматическую настройку:"
    echo "      ./scripts/setup_oauth.sh"
    echo ""
    exit 1
else
    echo "✅ GRAMAX_OAUTH_APPLICATION_ID: установлен"
    echo "   ID: ${APP_ID:0:20}..." # Показываем только первые 20 символов
fi

echo ""

if [ -z "$APP_SECRET" ]; then
    echo "ℹ️  GRAMAX_OAUTH_APPLICATION_SECRET: не установлен (опционально)"
    echo "   Это нормально для Public Applications"
else
    echo "✅ GRAMAX_OAUTH_APPLICATION_SECRET: установлен"
fi

echo ""
echo "📋 Следующие шаги:"
echo "   1. Убедитесь, что OAuth Application создано в GitLab"
echo "   2. Проверьте, что Redirect URI: http://localhost:8765/callback"
echo "   3. Попробуйте аутентификацию:"
echo "      gramax-sync auth login --oauth --url $GITLAB_URL"
echo ""
 