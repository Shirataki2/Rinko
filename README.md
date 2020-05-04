# Rinko

Discord Bot for Developers and Enginners

![](https://img.shields.io/badge/Version-0.8.5-green)

## Developing

1. **Make sure you have a Python version of 3.8 or higher**

Since this project is being developed using [pipenv](https://github.com/pypa/pipenv), we strongly recommend the introduction of pipenv.

```shell
pipenv install

# or

pip install -r requirements.txt
```

2. **Initialize the database.**

Please make sure that Mysql 8.0 is installed.

```shell
cd db
mv alembic.dev.ini alembic.ini
mysql -p
sql> CREATE DATABASE rinko;
```

Fill line 38 on alembic.ini.
```ini
sqlalchemy.url = mysql+pymysql://<username>:<password>@<host>/rinko
```

```shell
# Migrate
PYTHONPATH=. alembic revision --autogenerate
PYTHONPATH=. alembic upgrade head
```

3. **Create a Bot from the Discord Developer Portal and generate an OAuth2 URL to introduce a Bot with "administrator" privileges.**

Such as `https://discordapp.com/api/oauth2/authorize?client_id=xxxxxxxxxxxxxxxx&permissions=8&scope=bot`

4. **Get an access token to Bot.**

Such as `d2rRfO7iFkCIcAAfWW454VGf.w7IcX1WkRUT34ka7jpJK5TRXoLKLmZv0dC`

5. **Create config.ini on project root. And write as follows.**

```ini
[rinko]
bot_token=<your bot token>
log_level=DEBUG
mysql_user=<mysql user name>
mysql_passwd=<mysql password>
oauth2_url=<oauth2 url>
owner_id=<your User ID or 334017809090740224>
```

6. **Pull docker images**

```shell
docker pull python:3.8
docker pull theoldmoon0602/shellgeibot:20200430
docker pull golang:1.14
docker pull ruby:2.7.1
docker pull rust:1.43.0
docker pull php:7.4
docker pull node:14.0
docker pull haskell:8.8.3
docker pull openjdk:14
docker pull gcc:9.2
# etc ...
```

7. **Run**

```
python -m rinko config.ini
```

8. **Enjoy!**

## Requirements

- Python3.8+
- MySQL8.0
- v1.0.0 discord.py
- pipenv
- Docker 19.03