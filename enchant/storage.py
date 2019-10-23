#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import hashlib
import shutil

from pathlib import Path


def gen_object_id(file_path) -> str:
    """calculate object_id (akka sha1 sum) from file"""
    sha1 = hashlib.sha1()
    with open(file_path, 'rb') as f:
        while True:
            chunk = f.read(4096)
            if chunk:
                sha1.update(chunk)
            else:
                break
    return sha1.hexdigest()


def gen_path(storage_dir, object_id):
    assert (len(object_id) == 40)
    subdir = object_id[:2]
    filename = object_id[2:]
    return Path(storage_dir) / subdir / filename


def object_exists(storage_dir, object_id) -> bool:
    return Path(gen_path(storage_dir, object_id)).exists()


def save_object(storage_dir, file_path) -> str:
    """Save the file named file_path as a object and return the object_id.
    TODO: 生成 object_id 和 copyfile 都需读取文件内容，可优化为只读取一次。"""
    object_id = gen_object_id(file_path)
    object_path = gen_path(storage_dir, object_id)
    if not object_path.parent.exists():
        object_path.parent.mkdir(parents=True)
    shutil.copyfile(file_path, object_path)
    return object_id


def open_object(storage_dir, object_id, buffering=-1, encoding=None, errors=None,
                newline=None, closefd=True, opener=None):
    """open object as file, like the built-in open() function does."""
    path = gen_path(storage_dir, object_id)
    return open(path, buffering=buffering, encoding=encoding, errors=errors,
                newline=newline, closefd=closefd, opener=opener)
