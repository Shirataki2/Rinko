from configparser import ConfigParser
from sys import argv
from rinko.core.logger import get_module_logger

logger = get_module_logger(__name__)


class Config:
    cog_folder = "cogs"
    oauth2_url = ""
    owner_id = ""
    # DB
    mysql_user = ''
    mysql_passwd = ''
    mysql_host = 'localhost'
    mysql_db = 'rinko'
    # KEYS
    bot_token = ""
    # FORMATS
    log_level = "WARNING"

    def __init__(self, ini_file_path: str) -> None:
        parser = ConfigParser()
        try:
            parser.read(ini_file_path)
        except FileNotFoundError as e:
            logger.critical(f"{ini_file_path}が見つかりません")
            raise e
        config = parser["rinko"]
        logger.info(f'iniファイルより以下の設定を読み込みました')
        logger.info('=' * 64)
        for key in config:
            if hasattr(self, key):
                logger.info(f'\t{key}: {config[key]}')
                setattr(self, key, config[key])
        logger.info('=' * 64)


config = Config(argv[1])
