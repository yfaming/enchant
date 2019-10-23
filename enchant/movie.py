#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from sqlalchemy import MetaData, Table, Column, DateTime, Integer, String
from datetime import datetime

metadata = MetaData()


Movie = Table('movie', metadata,
    Column('id', Integer, primary_key=True),
    Column('name', String(256), nullable=False),
    Column('video_object_id', String(40), nullable=False, unique=True),
    Column('subtitle_object_id', String(40), nullable=False, unique=True),
    Column('subtitle_format', String(8), nullable=False),
    Column('created_at', DateTime, nullable=False)
)

def get_movie_by_id(conn, movie_id):
    sql = Movie.select().where(Movie.c.id == movie_id)
    return conn.execute(sql).fetchone()

def get_movie_by_subtitle_object_id(conn, subtitle_object_id):
    sql = Movie.select().where(Movie.c.subtitle_object_id == subtitle_object_id)
    return conn.execute(sql).fetchone()

def get_movie_by_video_object_id(conn, video_object_id):
    sql = Movie.select().where(Movie.c.video_object_id == video_object_id)
    return conn.execute(sql).fetchone()

def create_movie(conn, name, video_object_id, subtitle_object_id, subtitle_format):
    sql = Movie.insert().values(name=name,
                                video_object_id=video_object_id,
                                subtitle_object_id=subtitle_object_id,
                                subtitle_format=subtitle_format,
                                created_at=datetime.now())
    result = conn.execute(sql)
    return result.inserted_primary_key[0]


def delete_all(conn):
    sql = Movie.delete()
    conn.execute(sql)