#!/usr/bin/env python3
# # -*- coding: utf-8 -*-
import chardet
import logging
import os.path
import tempfile
from datetime import timedelta


def detect_encoding(file_path):
    raw = open(file_path, 'rb').read()
    res = chardet.detect(raw)
    if res['encoding'] in ('GB2312', 'GBK'):
        # GB18030 与 GB2312 和 GBK 兼容，且支持更多字符
        # 已发现有 chardet 检测出 GB2312 但打开文件时仍报解码错误的情况
        return 'GB18030'
    return res['encoding']


def file_to_utf8(file_path):
    """convert file encoding to utf-8 and newline to OS default line separator.
    It creates a tmp file, writes utf-8 encoded content into it, and returns\
    the path of the tmp file.
    """
    encoding = detect_encoding(file_path)
    _, tmppath = tempfile.mkstemp(prefix="enchant-" + os.path.basename(file_path) + '-')
    with open(file_path, encoding=encoding) as file, open(tmppath, 'w') as tmpfile:
        for line in file:
            tmpfile.write(line)
    return tmppath


def print_and_log(msg):
    print(msg)
    logging.info(msg)


def ffmpeg_timedelta(t: timedelta) -> str:
    """
    ffmpeg style: hh:mm:ss, no sub second parts
    将 timedelta 转为 hh:mm:ss 格式。
    ffmpeg 命令行似乎只能指定时间精度到「秒」，这里直接截断到秒。
    类 srt.timedelta_to_srt_timestamp，但后者精度为「毫秒」。
    """
    h, secs_remain = divmod(t.total_seconds(), 3600)
    m, secs_remain = divmod(secs_remain, 60)
    return '%02d:%02d:%02d' % (h, m, secs_remain)