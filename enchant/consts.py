#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os.path

SRT = '.srt'
ASS = '.ass'
SUPPORTED_SUBTITLE_FORMATS = (SRT, ASS)

MP4 = '.mp4'
MKV = '.mkv'
SUPPORTED_VIDEO_FORMATS = (MP4, MKV)

CONFIG_FILE = os.path.expanduser('~/.enchant.json')
LOG_FILE = os.path.expanduser('~/.enchant.log')