import pymysql
import configparser

_cfg = configparser.ConfigParser()
_cfg.read("config.ini", encoding="utf-8")

AVA_HOST = _cfg.get("ava_db", "host",     fallback="127.0.0.1")
AVA_PORT = int(_cfg.get("ava_db", "port", fallback="3306"))
AVA_USER = _cfg.get("ava_db", "user",     fallback="root")
AVA_PASS = _cfg.get("ava_db", "password", fallback="minju0416")
AVA_NAME = _cfg.get("ava_db", "name",     fallback="aibis")

BR_HOST  = _cfg.get("bridge_db", "host",     fallback="127.0.0.1")
BR_PORT  = int(_cfg.get("bridge_db", "port", fallback="3306"))
BR_USER  = _cfg.get("bridge_db", "user",     fallback="root")
BR_PASS  = _cfg.get("bridge_db", "password", fallback="minju0416")
BR_NAME  = _cfg.get("bridge_db", "name",     fallback="avalab")


def get_ava_conn():
    return pymysql.connect(
        host=AVA_HOST, port=AVA_PORT,
        user=AVA_USER, password=AVA_PASS,
        database=AVA_NAME,
        charset="euckr",
        cursorclass=pymysql.cursors.DictCursor,
    )


def get_bridge_conn():
    return pymysql.connect(
        host=BR_HOST, port=BR_PORT,
        user=BR_USER, password=BR_PASS,
        database=BR_NAME,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )


def init_bridge_db():
    conn = pymysql.connect(
        host=BR_HOST, port=BR_PORT,
        user=BR_USER, password=BR_PASS,
        charset="utf8mb4",
    )
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{BR_NAME}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
            cur.execute(f"USE `{BR_NAME}`")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS camera_bridge (
                    id         SMALLINT(5) UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
                    ava_cam_id SMALLINT(5) UNSIGNED NOT NULL,
                    node_id    VARCHAR(50) NOT NULL,
                    channel    SMALLINT(5) UNSIGNED NOT NULL,
                    camera_name VARCHAR(200) NOT NULL DEFAULT ''
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
        conn.commit()
    finally:
        conn.close()
