#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pathlib

import json
import logging
from enchant.consts import CONFIG_FILE
from enchant.exceptions import *

class Config(object):
    def __init__(self, repo_dir):
        self.repo_dir = repo_dir


def load_config() -> Config:
    p = pathlib.Path(CONFIG_FILE)
    if not p.exists():
        msg = '配置文件 %s 不存在'.format(CONFIG_FILE)
        raise EConfigNotFound(msg)

    with open(CONFIG_FILE) as file:
        try:
            dict = json.loads(file.read())
        except Exception as e:
            raise EConfigParseError('解析配置文件出错(读取错误或内容错误)')

        if 'repo' not in dict:
            logging.error('`repo` not found in config file')
            raise EConfigParseError('配置文件内容错误，无 repo 配置')
        return Config(dict['repo'])