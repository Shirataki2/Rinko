FROM centos:7

## PYTHON 3.8 ##

WORKDIR /opt

RUN yum -y update && yum upgrade
RUN yum -y groupinstall "Development Tools"
RUN yum -y install openssl-devel bzip2-devel libffi-devel ca-certificates
RUN yum -y install wget sudo curl
RUN wget https://www.python.org/ftp/python/3.8.2/Python-3.8.2.tgz
RUN tar xvf Python-3.8.2.tgz
RUN cd ./Python-3.8.2 && \
    ./configure --enable-optimizations && \
    make altinstall

## FFMPEG ##`

RUN yum -y update
RUN yum -y install epel-release
RUN rpm --import http://li.nux.ro/download/nux/RPM-GPG-KEY-nux.ro
RUN rpm -Uvh http://li.nux.ro/download/nux/dextop/el7/x86_64/nux-dextop-release-0-1.el7.nux.noarch.rpm
RUN yum -y install ffmpeg ffmpeg-devel

## MECAB ##

WORKDIR /opt
RUN git clone https://github.com/taku910/mecab.git
WORKDIR /opt/mecab/mecab
RUN ./configure  --enable-utf8-only \
  && make \
  && make check \
  && make install \
  && ldconfig

WORKDIR /opt/mecab/mecab-ipadic
RUN ./configure --with-charset=utf8 \
  && make \
  &&make install

WORKDIR /opt
RUN yum -y install which openssl
RUN git clone --depth 1 https://github.com/neologd/mecab-ipadic-neologd.git \
  && cd mecab-ipadic-neologd \
  && ./bin/install-mecab-ipadic-neologd -n -y \
  && cd .. \
  && rm -rf mecab-ipadic-neologd


## PIPENV ##

RUN yum -y update
RUN yum install -y https://centos7.iuscommunity.org/ius-release.rpm
RUN yum install -y python36u python36u-libs python36u-devel python36u-pip
RUN python3.6 -m pip install --upgrade pip

## DOCKER ##

RUN yum remove docker docker-client docker-client-latest docker-common docker-latest docker-latest-logrotate docker-logrotate docker-engine
RUN yum install -y yum-utils device-mapper-persistent-data lvm2
RUN yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
RUN yum install -y docker-ce docker-ce-cli containerd.io

## MYSQL CLIENT ##
RUN rpm -Uvh https://dev.mysql.com/get/mysql80-community-release-el7-1.noarch.rpm
RUN yum -y install mysql-community-client

## PIPENV ##

RUN localedef -f UTF-8 -i ja_JP ja_JP.UTF-8
ENV LANG="ja_JP.UTF-8" \
    LANGUAGE="ja_JP:ja" \
    LC_ALL="ja_JP.UTF-8"

COPY . /app/
WORKDIR /app
RUN pip3.8 install -r requirements.txt