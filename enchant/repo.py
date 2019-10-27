#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging
import math
import pathlib
import os.path
import subprocess
from datetime import datetime, timedelta

import ass
import srt
from sqlalchemy import create_engine
from sqlalchemy.engine.result import RowProxy
from whoosh.searching import ResultsPage

from enchant.consts import *
from enchant.exceptions import *
from enchant.movie import create_movie, metadata, \
    get_movie_by_subtitle_object_id, get_movie_by_video_object_id
from enchant.util import file_to_utf8, print_and_log, ffmpeg_timedelta
from enchant.storage import open_object, save_object, object_exists, gen_path
from enchant.search_engine import get_or_create_subtitle_index,\
    index_subtitle, search_subtitle


class Repo(object):
    """High level API"""
    def __init__(self, repo_dir):
        self.repo_dir = str(pathlib.Path(repo_dir).absolute())
        self.db = create_engine('sqlite:///{}'.format(self.db_path))

        # make sure directories and database are created
        if not pathlib.Path(self.storage_dir).exists():
            pathlib.Path(self.storage_dir).mkdir(parents=True)
        if not pathlib.Path(self.index_dir).exists():
            pathlib.Path(self.index_dir).mkdir(parents=True)
        if not pathlib.Path(self.db_path).exists():
            metadata.create_all(self.db)

    @property
    def storage_dir(self):
        return os.path.join(self.repo_dir, 'objects')

    @property
    def index_dir(self):
        return os.path.join(self.repo_dir, 'index')

    @property
    def db_path(self):
        return os.path.join(self.repo_dir, 'enchant.db')

    def submit_movie(self, video_path, subtitle_path):
        self._submit_movie_precheck(video_path, subtitle_path)
        conn = self.db.connect()
        video_object_id = self._submit_video_file(conn, video_path)
        subtitle_object_id, subtitle_format = self._index_subtitle_file(conn, subtitle_path)

        movie_name = pathlib.Path(video_path).name
        movie_id = create_movie(conn, movie_name, video_object_id, subtitle_object_id, subtitle_format)
        return movie_id

    def _submit_movie_precheck(self, video_path, subtitle_path):
        if not pathlib.Path(video_path).exists():
            raise EFileNotFound('文件不存在: {}'.format(video_path))
        _, ext = os.path.splitext(video_path)
        if ext.lower() not in SUPPORTED_VIDEO_FORMATS:
            msg = '视频格式不支持: {}。目前支持的格式包括: {}'\
                .format(ext, ' '.join(SUPPORTED_VIDEO_FORMATS))
            raise EVideoFormatNotSupported(msg)

        if not pathlib.Path(subtitle_path).exists():
            raise EFileNotFound('文件不存在: {}'.format(subtitle_path))
        _, ext = os.path.splitext(subtitle_path)
        if ext.lower() not in SUPPORTED_SUBTITLE_FORMATS:
            msg = '字幕格式不支持: {}。目前支持的格式包括: {}'\
                .format(ext, ' '.join(SUPPORTED_SUBTITLE_FORMATS))
            raise ESubtitleFormatNotSupported(msg)

    def _submit_video_file(self, conn, video_path):
        video_object_id = save_object(self.storage_dir, video_path)
        if get_movie_by_video_object_id(conn, video_object_id) is not None:
            raise EDuplicatedVideoFile('之前已提交过该视频，请勿重复提交')
        return video_object_id

    def _index_subtitle_file(self, conn, subtitle_path):
        subtitle_new_path = file_to_utf8(subtitle_path)
        subtitle_object_id = save_object(self.storage_dir, subtitle_new_path)
        if get_movie_by_subtitle_object_id(conn, subtitle_object_id) is not None:
            raise EDuplicatedSubtitleFile('之前已提交过该字幕，请勿重复提交')

        file = open_object(self.storage_dir, subtitle_object_id)
        index_writer = get_or_create_subtitle_index(self.index_dir).writer()
        _, ext = os.path.splitext(subtitle_path)
        index_subtitle(index_writer, subtitle_object_id, file, ext)
        return subtitle_object_id, ext

    def search_subtitle(self, query_string, pagenum=1, pagelen=15) -> ResultsPage:
        index = get_or_create_subtitle_index(self.index_dir)
        res = search_subtitle(index, query_string, pagenum, pagelen)
        return res

    def adjust_start_and_end(self, start: timedelta, end: timedelta,
                             pre_reserved_secs: timedelta,
                             post_reserved_secs: timedelta):
        start = start - pre_reserved_secs
        start = timedelta(seconds=math.floor(start.total_seconds()))
        if start.total_seconds() < 0:
            start = timedelta(seconds=0)
        end = end + post_reserved_secs
        end = timedelta(seconds=math.ceil(end.total_seconds()))
        return start, end

    def clip_video_and_subtitle(self, video_object_id: str, start: timedelta, end: timedelta,
                                pre_reserved_secs: timedelta, post_reserved_secs: timedelta):
        if not object_exists(self.storage_dir, video_object_id):
            raise EObjectNotFound('未找到对应视频: %s'.format(video_object_id))

        movie = get_movie_by_video_object_id(self.db.connect(), video_object_id)
        if not movie:
            raise EMovieNotFound('未找到对应视频: %s'.format(video_object_id))
        if not object_exists(self.storage_dir, movie.subtitle_object_id):
            raise EObjectNotFound('未找到对应字幕')

        start, end = self.adjust_start_and_end(start, end, pre_reserved_secs, post_reserved_secs)
        msg = 'real start={}, real_end={}' \
            .format(srt.timedelta_to_srt_timestamp(start),
                    srt.timedelta_to_srt_timestamp(end))
        print_and_log(msg)

        video_clip_path = self._gen_clip_filename(start, end, movie.name)
        self._clip_video(movie, start, end, video_clip_path)
        self._clip_subtitle(movie, start, end, video_clip_path)

    def _gen_clip_filename(self, start: timedelta, end: timedelta, movie_name):
        """形如 20191022125808_002154_to_002157.S01E01.mkv.mp4"""
        TMPL = '{now}_{start}_to_{end}.{movie_name}.mp4'
        nowstr = datetime.now().strftime('%Y%m%d%H%M%S')
        startstr = ffmpeg_timedelta(start).replace(':', '')
        endstr = ffmpeg_timedelta(end).replace(':', '')
        return TMPL.format(now=nowstr, start=startstr, end=endstr, movie_name=movie_name)

    def _clip_video(self, movie: RowProxy, start: timedelta, end: timedelta, video_clip_path):
        ffmpeg = 'ffmpeg -ss {start} -t {duration} -i {video_path} -c:v libx264 -c:a aac {video_clip_path}'

        video_path = gen_path(self.storage_dir, movie.video_object_id)
        duration = int((end - start).total_seconds())
        ffmpeg = ffmpeg.format(start=ffmpeg_timedelta(start),
                               duration=duration,
                               video_path=video_path,
                               video_clip_path=video_clip_path)

        print_and_log('executing: {}'.format(ffmpeg))
        proc = subprocess.run(ffmpeg.split(' '),
                              stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT,
                              encoding='utf-8',
                              check=True)
        logging.info(proc.stdout)

    def _clip_subtitle(self, movie: RowProxy, start: timedelta, end: timedelta, video_clip_path):
        subtitle_clip_path = video_clip_path + movie.subtitle_format
        file = open_object(self.storage_dir, movie.subtitle_object_id)
        if movie.subtitle_format == SRT:
            subtitles = [sub for sub in srt.parse(file) if start <= sub.start <= sub.end <= end]
            for sub in subtitles:
                sub.start -= start
                sub.end -= start
            with open(subtitle_clip_path, 'w') as f:
                f.write(srt.compose(subtitles))
        else:
            doc = ass.parse(file)
            events = [e for e in doc.events if start <= e.Start <= e.End <= end]
            for e in events:
                e.Start -= start
                e.End -= end
            doc.events = events
            with open(subtitle_clip_path, 'w') as f:
                doc.dump_file(f)
