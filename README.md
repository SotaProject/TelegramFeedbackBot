# TelegramFeedbackBot

TelegramFeedbackBot – под предложки, вам смогут писать читатели, а вы сможете анонимно отвечать.



## Подготовка к запуску

1. Создаем в https://t.me/BotFather бота, получаем его токен
2. Создаем чат, добавляем туда бота и всех, кто будет в нем отвечать. ВАЖНО: Телеграм чат может стать супергруппый при некоторых условиях, в этот момент он меняет ID, лучше сразу превратить его в супергруппу сделав одного из участников админом.

## Запуск

1. Получаем ID чата, например через этого бота https://t.me/myidbot
2. Создаем папку, скажем `mkdir /opt/my_bot` и переходим в нее `cd /opt/my_bot`.

2. Клонируем репозиторий `git clone https://github.com/SotaProject/TelegramFeedbackBot.git`
3. Скачиваем docker-compose.yaml: `curl https://gist.githubusercontent.com/sijokun/07a1517f7917e6970ce12708be45de2c/raw/a00ba12b5e9cec37cad32d403d491ff12a4eb085/telegram_feedback_bot.%25D1%2581ompose.yaml > docker-compose.yaml`
4. Открываем docker-compose.yaml в удобном нам редакторе, скажем `nano  docker-compose.yaml`
5. Меняем пароль от БД (в двух местах), токен бота и ид группы. Редактируем START_TEXT под себя.
6. Запускаем через `docker compose up -d` 

## Кастомные команды

В боте можно добавить кастомные команды, на них бот будет отвечать заданным текстом. Команды задаются в config.py.

1. Скопируйте config.py из папки с кодом, мы его прокинем «поверх» оригинального файла.

2. Отредактируйте в config.py команды и тексты ответа на них, через set_command и description можно задать добавление команды в меню бота.

3. Добавьте в docker-compose.yaml проброс файла 

   ``` 
   volumes:
     - ./config.py:/app/config.py
   ```

4. Перезапустите контейнер.
