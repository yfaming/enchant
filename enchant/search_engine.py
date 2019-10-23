#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import pathlib
from typing import Iterable

import ass
import srt
from whoosh import index
from whoosh.fields import *
from whoosh.qparser import QueryParser
from whoosh.searching import ResultsPage

from enchant.consts import *
from enchant.exceptions import ESubtitleFormatNotSupported

subtitle_schema = Schema(object_id=ID(stored=True),  # subtitle object id
                         start=ID(stored=True),  # start time, str, like 01:23:04,000
                         end=ID(stored=True),    # end time, str, like 01:23:08,000
                         content=TEXT(stored=True),
                         idx=NUMERIC(stored=True))    # index

SUBTITLE_INDEX_NAME = 'index_subtitles'


def get_or_create_subtitle_index(index_dir):
    # make sure directory exist
    if not pathlib.Path(index_dir).exists():
        pathlib.Path(index_dir).mkdir(parents=True)
    # make sure index exist
    if index.exists_in(index_dir, SUBTITLE_INDEX_NAME):
        return index.open_dir(index_dir, SUBTITLE_INDEX_NAME)
    else:
        return index.create_in(index_dir, subtitle_schema, SUBTITLE_INDEX_NAME)


def _index_srt(writer, object_id: str, subtitles: Iterable[srt.Subtitle]):
    for subtitle in subtitles:
        writer.add_document(object_id=object_id,
                            start=srt.timedelta_to_srt_timestamp(subtitle.start),
                            end=srt.timedelta_to_srt_timestamp(subtitle.end),
                            content=subtitle.content,
                            idx=subtitle.index)


def _index_ass(writer, object_id: str, evevnts: Iterable[ass.document.Dialogue]):
    for idx, event in enumerate(evevnts):
        writer.add_document(object_id=object_id,
                            start=srt.timedelta_to_srt_timestamp(event.Start),
                            end=srt.timedelta_to_srt_timestamp(event.End),
                            content=event.Text,
                            idx=idx)

def index_subtitle(index_writer, object_id, file, format):
    if format not in SUPPORTED_SUBTITLE_FORMATS:
        raise ESubtitleFormatNotSupported(format)

    try:
        if format == SRT:
            subtitles = srt.parse(file)
            _index_srt(index_writer, object_id, subtitles)
        else:
            doc = ass.parse(file)
            _index_ass(index_writer, object_id, doc.events)
        index_writer.commit()
    except Exception as e:
        index_writer.cancel()
        raise e


def search_subtitle(subtitle_index, query_string, pagenum=1, pagelen=10) -> ResultsPage:
    """pagenum starts at 1."""
    qp = QueryParser("content", subtitle_index.schema)
    query = qp.parse(query_string)
    return subtitle_index.searcher().search_page(query, pagenum, pagelen)