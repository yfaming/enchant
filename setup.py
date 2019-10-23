from setuptools import setup

setup(
    name='enchant',
    version='0.0.1',
    packages=['enchant'],
    url='',
    license='',
    author='yfaming',
    author_email='yfaming@gmail.com',
    description='A movie subtitle searcher and video clip maker',
    install_requires=[
        "chardet>=3.0",
        "whoosh>=2.7",
        "srt>=3.0",
        "ass>=0.4",
        "sqlalchemy>=1.3",
        "prompt-toolkit>=2.0"
    ],
    entry_points={
        'console_scripts': ['enchant = enchant.main:main']
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy',
    ]
)
