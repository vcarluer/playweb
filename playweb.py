import logging
import urllib
import os
from string import Template
import requests
import json
from flask import Flask, render_template
app = Flask(__name__)

logging.getLogger().setLevel(logging.DEBUG)
baseDir = 'static/ms/'

@app.route('/')
def root():
    return directory(baseDir)

@app.route('/<key>')
def directory(key):
    dirPath = getPath(key)
    dirInfo = DirectoryInfo(dirPath)
    if len(dirInfo.movies) == 1:
        return info(dirInfo.movies[0].key)
    else:
        return render_template('movies.html', dirs=dirInfo.directories, movies=dirInfo.movies)

@app.route('/video/<key>')
def movie(key):
    moviePath = getPath(key)
    movie = MovieInfo(moviePath)
    app.logger.debug('rendering template video for: ' + movie.path)
    return render_template('video.html', movie=movie)

@app.route('/info/<key>')
def info(key):
    moviePath = getPath(key)
    movie = MovieInfo(moviePath)
    app.logger.debug('rendering template video info: ' + movie.path)
    return render_template('info.html', movie=movie)

def getKey(path):
    return urllib.parse.quote(path.replace('/', '_-'))

def getPath(key):
    return urllib.parse.unquote(key.replace('_-', '/'))


class DirectoryInfo():
    def __init__(self, path):
        self.directories = []
        self.movies = []
        self.name = os.path.basename(path)
        self.key = getKey(path)

        for subItem in os.listdir(path):
            app.logger.debug('Handling item: ' + subItem)
            subDirPath = os.path.join(path, subItem)
            if os.path.isdir(subDirPath):
                app.logger.debug('Add directory ' + subItem)
                dirItem = DirectoryItem(subItem, subDirPath)
                self.directories.append(dirItem)
            else:
                # Search for jackett here
                extsplit = os.path.splitext(subItem)
                if len(extsplit) > 1:
                    name = extsplit[0]
                    ext = extsplit[1]
                    app.logger.debug('Handling extension: ' + ext)
                    if ext == '.mp4':
                        movieItem = MovieItem(path, name, ext)
                        self.movies.append(movieItem)

        app.logger.debug('Directory info count:')
        app.logger.debug('Directories:' + str(len(self.directories)))
        app.logger.debug('Movies:' + str(len(self.movies)))

class MovieInfo():
    def __init__(self, path):
        self.path = path
        self.key = getKey(path)
        self.fileName = os.path.basename(self.path)
        extsplit = os.path.splitext(self.fileName)
        self.name = os.path.basename(os.path.dirname(self.path))
        self.fileName = extsplit[0]
        self.ext = extsplit[1]
        self.subtitles = []
        self.isEpisode = False
        # Subtitles here

        # Other movie infos
        self.tmdb = TmdbInfo(self.name)

class TmdbInfo():
    tmdbapi = '372020cd232e0239905b1b2ad473c208'
    searchUrl = Template('https://api.themoviedb.org/3/search/movie?api_key=$apikey&query=$query')

    def __init__(self, name):
        self.origName = name
        r = self.search_tmdb(name)
        self.tmdb = r
        self.parse_result(r)

    def parse_result(self, r):
        self.count = int(r['total_results'])
        app.logger.debug('total result: ' + str(self.count))
        if self.count > 0:
            self.id = r['results'][0]['id']
            app.logger.debug('themoviedb id: ' + str(self.id))
            self.poster = r['results'][0]['poster_path']
            app.logger.debug('themoviedb poster: ' + str(self.poster))

    def search_tmdb(self, name):
        searchName = name
        datePos = searchName.find(' (')
        if datePos > -1:
            searchName = searchName[:datePos]

        nameEscape = urllib.parse.quote(searchName)
        searchQuery = TmdbInfo.searchUrl.substitute(apikey=TmdbInfo.tmdbapi, query=nameEscape)
        app.logger.debug('querying ' + searchQuery)
        result = requests.get(searchQuery)
        app.logger.debug(result.json())
        r = json.loads(result.content.decode('utf-8'))
        return r

class DirectoryItem():
    def __init__(self, name, path):
        self.key = getKey(path)
        self.name = name
        self.path = path
        # Search for jackett here

class MovieItem():
    def __init__(self, base, name, ext):
        self.base = base
        self.name = name
        self.ext = ext

        self.path = os.path.join(self.base, self.name) + self.ext
        self.key = getKey(self.path)
        # Search for jackett here

'''class Movie():
    def __init__(self, path, expand=False):
        self.path = path
        self.title = os.path.basename(path)
        self.key = urllib.parse.quote(path.replace('/', '_-'))
        self.subtitles = []
        self.videoPath = ''
        self.ismovie = False
        self.url = '/' + self.key
        if expand:
            movieDirFiles = os.listdir(self.path)
            app.logger.debug('Number of files in movie dir:' + str(len(movieDirFiles)))
            for movieFile in movieDirFiles:
                mfPath = self.path + '/' + movieFile
                urlPath = '/' + mfPath
                if os.path.isfile(mfPath):
                    app.logger.debug('Handling file: ' + mfPath)
                    extsplit = os.path.splitext(movieFile)
                    if len(extsplit) > 1:
                        ext = extsplit[1]
                        app.logger.debug('Handling extension: ' + ext)
                        if ext == '.mp4':
                            self.videoPath = urlPath
                            self.ismovie = True
                            self.url = '/video/' + self.key
                        if ext == '.vtt':
                            subPath = urlPath
                            subLabel = 'Unknown'
                            subDefault = ''
                            subLang = 'en'
                            if movieFile.find('.fr') != -1:
                                subLabel = 'French'
                                subDefault = 'default'
                                subLang = 'fr'
                            if movieFile.find('.en') != -1:
                                subLabel = 'English'

                            subtitle = Subtitle(subPath, subLabel, subDefault, subLang)
                            self.subtitles.append(subtitle)
                            '''

class Subtitle:
    def __init__(self, path, label, default, lang):
        self.path = path
        self.label = label
        self.default = default
        self.lang = lang

