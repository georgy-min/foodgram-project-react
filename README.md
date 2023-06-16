# FOODGRAM. Продуктовый помощник

# О проекте:
Приложение FOODGRAM «Продуктовый помощник»: сайт, на котором пользователи могут публиковать рецепты, добавлять чужие рецепты в избранное и подписываться на публикации других авторов. Сервис «Список покупок» позволит пользователям создавать список продуктов, которые нужно купить для приготовления выбранных блюд. 

# Подготовка и запуск проекта

## Склонируйте репозиторий:
```sh
git clone git@github.com:georgy-min/foodgram-project-react.git
```
## Установите docker на сервер:

```sh
sudo apt install docker.io 
```
## Установите docker-compose на сервер:

```sh
sudo curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```
## Создайте файл содержащий переменные виртуального окружения (.env)

```sh
cd foodgram-project-react
touch .env
```
```sh
DB_ENGINE=<django.db.backends.postgresql>
DB_NAME=<имя базы данных postgres>
DB_USER=<пользователь бд>
DB_PASSWORD=<пароль>
DB_HOST=<db>
DB_PORT=<5432>
```

## Разверните контейнеры и выполните миграции:

```sh
cd foodgram-project-react/infra/
sudo docker-compose up -d --build
sudo docker-compose exec backend python3 manage.py migrate
```
## Создайте суперюзера:

```sh
sudo docker-compose exec backend python3 manage.py createsuperuser
```
## Соберите статику:

```sh
sudo docker-compose exec backend python3 manage.py collectstatic --no-input
```
Загрузите ингридиенты и теги в базу данных: 

```sh
sudo docker-compose exec backend python manage.py load_all_data
sudo docker-compose exec backend python manage.py fill_tags
```


## Для дальнейшего создания фикстур из Вашей БД, используйте команду:
```sh
sudo docker-compose exec backend python3 manage.py dumpdata > fixtures.json
```

## Автор

[Георгий Минин](https://github.com/georgy-min/)
