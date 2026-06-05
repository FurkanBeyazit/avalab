import pymysql
import configparser

_cfg = configparser.ConfigParser()
_cfg.read("config.ini", encoding="utf-8")

AVA_STOR_HOST = _cfg.get("ava_stor", "host", fallback="172.20.14.161")
AVA_STOR_PORT = int(_cfg.get("ava_stor", "port", fallback="9080"))

BR_HOST = _cfg.get("bridge_db", "host",     fallback="127.0.0.1")
BR_PORT = int(_cfg.get("bridge_db", "port", fallback="3306"))
BR_USER = _cfg.get("bridge_db", "user",     fallback="root")
BR_PASS = _cfg.get("bridge_db", "password", fallback="minju0416")
BR_NAME = _cfg.get("bridge_db", "name",     fallback="avalab")


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
                    id            SMALLINT(5) UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
                    ava_cam_id    VARCHAR(20)  NOT NULL,
                    node_id       VARCHAR(50)  NOT NULL,
                    channel       SMALLINT(5) UNSIGNED NOT NULL,
                    name          VARCHAR(200) NOT NULL DEFAULT '',
                    stor_ip       VARCHAR(50)  NOT NULL DEFAULT '',
                    ip            VARCHAR(50)  NOT NULL DEFAULT '',
                    port          VARCHAR(20)  NOT NULL DEFAULT '',
                    rtsp_main_url VARCHAR(500) NOT NULL DEFAULT '',
                    lat           VARCHAR(30)  NOT NULL DEFAULT '',
                    lng           VARCHAR(30)  NOT NULL DEFAULT ''
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
            # Migration: add columns to existing tables
            for col, definition in [
                ("stor_ip",       "VARCHAR(50)  NOT NULL DEFAULT ''"),
                ("ip",            "VARCHAR(50)  NOT NULL DEFAULT ''"),
                ("port",          "VARCHAR(20)  NOT NULL DEFAULT ''"),
                ("rtsp_main_url", "VARCHAR(500) NOT NULL DEFAULT ''"),
                ("lat",           "VARCHAR(30)  NOT NULL DEFAULT ''"),
                ("lng",           "VARCHAR(30)  NOT NULL DEFAULT ''"),
            ]:
                cur.execute(
                    f"ALTER TABLE camera_bridge ADD COLUMN IF NOT EXISTS `{col}` {definition}"
                )
            # ava_cam_id type change: SMALLINT → VARCHAR (safe: numeric strings still match)
            try:
                cur.execute(
                    "ALTER TABLE camera_bridge MODIFY COLUMN ava_cam_id VARCHAR(20) NOT NULL"
                )
            except Exception:
                pass

            cur.execute("""
                CREATE TABLE IF NOT EXISTS event_area (
                    id              INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
                    camera_id       VARCHAR(20)  NOT NULL,
                    event_type      SMALLINT(5) UNSIGNED NOT NULL,
                    geometry        TEXT NOT NULL DEFAULT '',
                    activation_time VARCHAR(20) NOT NULL DEFAULT '00:00-24:00',
                    UNIQUE KEY uq_cam_event (camera_id, event_type)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)
        conn.commit()
    finally:
        conn.close()
