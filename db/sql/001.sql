CREATE DATABASE IF NOT EXISTS rinko;
USE rinko;

CREATE TABLE IF NOT EXISTS `reminder` (
    `id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `guild` VARCHAR(64) NOT NULL,
    `user` VARCHAR(64) NOT NULL,
    `text` VARCHAR(64) NOT NULL,
    `start_at` DATETIME,
    `created_at` DATETIME
);

CREATE TABLE IF NOT EXISTS `reminder_channel` (
    `guild` VARCHAR(64) UNIQUE NOT NULL,
    `channel` VARCHAR(64) NOT NULL
);

CREATE TABLE IF NOT EXISTS `reminder_call` (
    `guild` VARCHAR(64) UNIQUE NOT NULL,
    `7d` BOOLEAN,
    `1d` BOOLEAN,
    `12H` BOOLEAN,
    `6H` BOOLEAN,
    `3H` BOOLEAN,
    `2H` BOOLEAN,
    `1H` BOOLEAN,
    `30M` BOOLEAN,
    `10M` BOOLEAN,
    `0M` BOOLEAN
);

CREATE TABLE IF NOT EXISTS `server_info` (
    `guild` VARCHAR(64) UNIQUE NOT NULL,
    `locale` VARCHAR(64) NOT NULL,
    `prefix` VARCHAR(64) NOT NULL,
    `enable_quote` BOOLEAN
);

CREATE TABLE IF NOT EXISTS `wallet` (
    `guild` VARCHAR(64) NOT NULL,
    `user` VARCHAR(64) NOT NULL,
    `money` INT NOT NULL,
    `turnip` INT NOT NULL,
    `rotten_turnip` INT NOT NULL,
    `buy_at` DATETIME
);


CREATE TABLE IF NOT EXISTS `works` (
    `guild` VARCHAR(64) NOT NULL,
    `user` VARCHAR(64) NOT NULL,
    `date` DATETIME
);

CREATE TABLE IF NOT EXISTS `turnip` (
    `price` FLOAT NOT NULL,
    `type` VARCHAR(64) NOT NULL,
    `date` DATETIME
);
