#!/bin/sh

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

python3.8 -m rinko config.prod.ini

exec "$@"