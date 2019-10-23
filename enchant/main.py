#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse
import logging
import logging.config
import pathlib
import sys
import traceback
from datetime import timedelta

import srt

from enchant.config import load_config
from enchant.consts import LOG_FILE
from enchant.exceptions import *
from enchant.movie import get_movie_by_id, get_movie_by_subtitle_object_id
from enchant.repo import Repo
from enchant.util import print_and_log


def config_log(log_filename):
    logging.config.dictConfig({
        'version': 1,
        'disable_existing_loggers': True,
        'formatters': {
            'default': {
                'format': '%(asctime)s %(levelname)s %(name)s %(message)s'
            },
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'stream': 'ext://sys.stderr',
                'formatter': 'default',
                'level': 'ERROR',
            },
            'file': {
                'class': 'logging.FileHandler',
                'filename': log_filename,
                'formatter': 'default',
                'level': 'DEBUG',
            }
        },
        'root': {
            # can enable console for debugging
            'handlers': ['file'],
            'level': 'INFO',
        },
    })


def get_repo_or_exit():
    try:
        config = load_config()
        repo = Repo(config.repo_dir)
        return repo
    except EConfigNotFound:
        print('enchant 未经初始化配置，请执行以下命令:')
        print('enchant init')
        sys.exit(0)
    except EConfigParseError as e:
        print(e.msg)
        logging.exception(e.msg)
        sys.exit(1)
    except Exception as e:
        logging.exception('encountered unkown error')
        traceback.print_tb(e.__traceback__)
        sys.exit(1)


DEFAULT_PRE_RESERVED_SECS = 0.5
DEFAULT_POST_RESERVED_SECS = 2.0


def init_arg_parser():
    parser = argparse.ArgumentParser(prog='enchant', description='a movie subtitle searcher and video clip maker')
    subparsers = parser.add_subparsers(dest='cmd', title='subcommands')
    # cmd init
    parser_init = subparsers.add_parser('init', help='init enchant')
    parser_init.set_defaults(func=cmd_init)
    # cmd submit
    parser_submit = subparsers.add_parser('submit', help='submit a movie and its subtitle to make it searchable')
    parser_submit.add_argument('--video', required=True, help='video path')
    parser_submit.add_argument('--subtitle', required=True, help='subtitle path')
    parser_submit.set_defaults(func=cmd_submit)
    # cmd search
    parser_search = subparsers.add_parser('search', help='search some keyword in subtitles')
    parser_search.add_argument('keyword', help='the word you want to search')
    parser_search.add_argument('--pagenum', type=int, default=1, help='page number, defaults to 1')
    parser_search.add_argument('--pagelen', type=int, default=15, help='result numbers per page, defaults to 15')
    parser_search.add_argument('--auto_clip_all', action='store_true',
                               help='automatically make clips for search result')
    parser_search.add_argument('--pre_reserved_secs', type=float, default=DEFAULT_PRE_RESERVED_SECS,
                               help='extra seconds before start will be clipped. defaults to {}. works only when --auto_clip_all is enabled'.format(DEFAULT_PRE_RESERVED_SECS))
    parser_search.add_argument('--post_reserved_secs', type=float, default=DEFAULT_POST_RESERVED_SECS,
                               help='extra seconds after end will be clipped. defaults to {}. workds only when --auto_clip_all is enabled'.format(DEFAULT_POST_RESERVED_SECS))
    parser_search.set_defaults(func=cmd_search)

    # cmd clip
    parser_clip = subparsers.add_parser('clip', help='make a clip from movie')
    parser_clip.add_argument('--start', required=True, type=srt.srt_timestamp_to_timedelta, help='start time')
    parser_clip.add_argument('--end', required=True, type=srt.srt_timestamp_to_timedelta, help='end time')
    parser_clip.add_argument('--video_object_id', required=True, help='video object id')
    parser_clip.add_argument('--pre_reserved_secs', type=float, default=0.5,
                             help='extra seconds before start will be clipped. defaults to {}'.format(DEFAULT_PRE_RESERVED_SECS))
    parser_clip.add_argument('--post_reserved_secs', type=float, default=2,
                             help='extra seconds after end will be clipped. defaults to {}'.format(DEFAULT_POST_RESERVED_SECS))
    parser_clip.set_defaults(func=cmd_clip)
    return parser


def main():
    config_log(LOG_FILE)
    logging.info('enchant running...')
    logging.info('cwd: %s', pathlib.Path.cwd())
    logging.info('cmd: %s', ' '.join(sys.argv))

    try:
        parser = init_arg_parser()
        args = parser.parse_args()
        if not args.cmd:
            parser.print_help()
            sys.exit(1)
        args.func(args)
    except EnchantException as e:
        print(e.msg)
        logging.exception(e.msg)
        sys.exit(1)
    except Exception as e:
        logging.exception('encountered unkown error')
        traceback.print_tb(e.__traceback__)
        sys.exit(1)


def cmd_init(args):
    """TODO: 看来需要写命令行交互...
    或者用自带的 Tk?"""
    _ = args


def cmd_submit(args):
    repo = get_repo_or_exit()
    video_path, subtitle_path = args.video, args.subtitle
    movie_id = repo.submit_movie(video_path, subtitle_path)
    movie = get_movie_by_id(repo.db.connect(), movie_id)
    assert movie is not None
    msg = 'submission succeeded! movie_id: {}, video_object_id: {}, subtitle_object_id: {}' \
        .format(movie_id, movie.video_object_id, movie.subtitle_object_id)
    print_and_log(msg)


def cmd_search(args):
    repo = get_repo_or_exit()
    keyword, pagenum, pagelen = args.keyword, args.pagenum, args.pagelen
    respage = repo.search_subtitle(keyword, pagenum, pagelen)
    if not respage:
        msg = 'Nothong Found.'
        print_and_log(msg)
        return

    msg = 'page {}/{}, result {} - {} of total {}.' \
        .format(respage.pagenum, respage.pagecount,
                respage.offset + 1, respage.offset + respage.pagelen, respage.total)
    print_and_log(msg)

    for item in respage:
        subtitle_object_id = item['object_id']
        start, end, content = item['start'], item['end'], item['content']
        movie = get_movie_by_subtitle_object_id(repo.db.connect(), subtitle_object_id)

        print_and_log('{} {}-->{} {}'.format(content.replace('\n', ' '), start, end, movie.name))
        clip_cmd = 'CMD: enchant clip --start {} --end {} --video_object_id {}'\
            .format(start, end, movie.video_object_id)
        print_and_log(clip_cmd)
        print_and_log('')

    if args.auto_clip_all:
        print_and_log('automatically make clips for search result:')
        for item in respage:
            movie = get_movie_by_subtitle_object_id(repo.db.connect(), item['object_id'])
            start = srt.srt_timestamp_to_timedelta(item['start'])
            end = srt.srt_timestamp_to_timedelta(item['end'])
            repo.clip_video_and_subtitle(movie.video_object_id, start, end,
                                         timedelta(seconds=args.pre_reserved_secs),
                                         timedelta(seconds=args.post_reserved_secs))


def cmd_clip(args):
    video_object_id = args.video_object_id
    repo = get_repo_or_exit()
    repo.clip_video_and_subtitle(video_object_id, args.start, args.end,
                                 timedelta(seconds=args.pre_reserved_secs),
                                 timedelta(seconds=args.post_reserved_secs))


if __name__ == '__main__':
    main()
