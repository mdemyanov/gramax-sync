#!/bin/bash
# Скрипт для настройки OAuth Application для gramax-sync

set -e

GITLAB_URL="${1:-https://itsmf.gitlab.yandexcloud.net}"
APP_NAME="gramax-sync"
REDIRECT_URI="http://localhost:8765/callback"

echo "🔧 Настройка OAuth Application для gramax-sync"
echo "=============================================="
echo ""
echo "📍 GitLab URL: $GITLAB_URL"
echo "📱 Application Name: $APP_NAME"
echo "🔗 Redirect URI: $REDIRECT_URI"
echo ""
echo "📋 ШАГ 1: Создание OAuth Application в GitLab"
echo "---------------------------------------------"
echo ""
echo "1. Откройте в браузере:"
echo "   $GITLAB_URL/-/profile/applications"
echo ""
echo "2. Нажмите 'Add new application' (или 'New application')"
echo ""
echo "3. Заполните форму:"
echo "   - Name: $APP_NAME"
echo "   - Redirect URI: $REDIRECT_URI"
echo "   - Scopes: выберите все три:"
echo "     ✅ read_api"
echo "     ✅ read_repository"
echo "     ✅ write_repository"
echo ""
echo "4. Нажмите 'Save application'"
echo ""
echo "5. Скопируйте Application ID (это длинная строка)"
echo ""
read -p "📥 Введите Application ID: " APPLICATION_ID

if [ -z "$APPLICATION_ID" ]; then
    echo "❌ Ошибка: Application ID не может быть пустым!"
    exit 1
fi

echo ""
read -p "🔐 Введите Application Secret (если есть, иначе нажмите Enter): " APPLICATION_SECRET

echo ""
echo "📋 ШАГ 2: Установка переменных окружения"
echo "---------------------------------------------"
echo ""

# Определяем shell config файл
if [ -f "$HOME/.zshrc" ]; then
    SHELL_CONFIG="$HOME/.zshrc"
elif [ -f "$HOME/.bashrc" ]; then
    SHELL_CONFIG="$HOME/.bashrc"
elif [ -f "$HOME/.bash_profile" ]; then
    SHELL_CONFIG="$HOME/.bash_profile"
else
    SHELL_CONFIG="$HOME/.profile"
fi

echo "Добавляю переменные в $SHELL_CONFIG..."

# Удаляем старые значения, если есть
sed -i.bak "/^export GRAMAX_OAUTH_APPLICATION_ID=/d" "$SHELL_CONFIG" 2>/dev/null || true
sed -i.bak "/^export GRAMAX_OAUTH_APPLICATION_SECRET=/d" "$SHELL_CONFIG" 2>/dev/null || true

# Добавляем новые значения
echo "" >> "$SHELL_CONFIG"
echo "# OAuth Application для gramax-sync" >> "$SHELL_CONFIG"
echo "export GRAMAX_OAUTH_APPLICATION_ID=\"$APPLICATION_ID\"" >> "$SHELL_CONFIG"

if [ -n "$APPLICATION_SECRET" ]; then
    echo "export GRAMAX_OAUTH_APPLICATION_SECRET=\"$APPLICATION_SECRET\"" >> "$SHELL_CONFIG"
fi

echo "✅ Переменные окружения добавлены в $SHELL_CONFIG"
echo ""
echo "📋 ШАГ 3: Применение изменений"
echo "---------------------------------------------"
echo ""
echo "Выполните одну из команд для применения изменений:"
echo ""
echo "  source $SHELL_CONFIG"
echo ""
echo "Или перезапустите терминал"
echo ""
echo "📋 ШАГ 4: Проверка"
echo "---------------------------------------------"
echo ""
echo "Проверьте, что переменные установлены:"
echo ""
echo "  echo \$GRAMAX_OAUTH_APPLICATION_ID"
echo ""
echo "Должно вывести: $APPLICATION_ID"
echo ""
echo "✅ Настройка завершена!"
echo ""
echo "🚀 Теперь вы можете использовать OAuth аутентификацию:"
echo "   gramax-sync auth login --oauth --url $GITLAB_URL"
echo ""

