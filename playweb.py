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
        return render_template('movies.html', name=dirInfo.name, dirs=dirInfo.directories, movies=dirInfo.movies)

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
    searchUrl = Template('https://api.themoviedb.org/3/search/$mtype?api_key=$apikey&query=$query')
    posterUrl = Template('https://image.tmdb.org/t/p/w185$poster')
    mediaUrl = Template('https://www.themoviedb.org/$mtype/$tmdbid')

    def __init__(self, name, mtype = 'movie'):
        self.mtype = mtype
        self.origName = name
        r = self.search_tmdb(name, self.mtype)
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
            self.url = TmdbInfo.mediaUrl.substitute(mtype=self.mtype,tmdbid=self.id)
            self.posterUrl = TmdbInfo.posterUrl.substitute(poster=self.poster)
        else:
            self.id = -1
            self.poster = ''
            self.url = ''
            self.posterUrl = ''

    def search_tmdb(self, name, mtype = 'movie'):
        self.searchName = name
        datePos = self.searchName.find(' (')
        if datePos > -1:
            self.searchName = self.searchName[:datePos]

        nameEscape = urllib.parse.quote(self.searchName)
        searchQuery = TmdbInfo.searchUrl.substitute(mtype=mtype, apikey=TmdbInfo.tmdbapi, query=nameEscape)
        app.logger.debug('querying ' + searchQuery)
        result = requests.get(searchQuery)
        app.logger.debug(result.json())
        r = json.loads(result.content.decode('utf-8'))
        return r

class TmdbSeasonInfo():
    seasonGetUrl = Template('https://api.themoviedb.org/3/tv/$tv_id/season/$season_number?api_key=$apikey')
    seasonUrl = Template('https://www.themoviedb.org/$mtype/$tmdbid/season/$season')

    def __init__(self, tvid, season):
        self.tvid = tvid
        self.season = season
        self.get_season()
        self.parse_result()

    def get_season(self):
        getQuery = TmdbSeasonInfo.seasonGetUrl.substitute(tv_id=self.tvid, season_number=self.season,apikey=TmdbInfo.tmdbapi)
        app.logger.debug('querying ' + getQuery)
        result = requests.get(getQuery)
        app.logger.debug(result.json())
        self.tmdb = json.loads(result.content.decode('utf-8'))

    def parse_result(self):
        if not self.tmdb['id'] == None:
            self.id = self.tmdb['id']
            app.logger.debug('setting season id to ' + str(self.id))
            self.url = TmdbSeasonInfo.seasonUrl.substitute(mtype='tv',tmdbid=self.tvid,season=str(self.season))
        else:
            self.url = ''

        if not self.tmdb['poster_path'] == None:
            self.poster = self.tmdb['poster_path']
            app.logger.debug('setting season poster to ' + self.poster)
            self.posterUrl = TmdbInfo.posterUrl.substitute(poster=self.poster)
        else:
            self.posterUrl = ''

class DirectoryItem():
    def __init__(self, name, path):
        self.key = getKey(path)
        self.name = name
        self.path = path

        seasonPos = name.find('Season ')
        if not seasonPos == -1:
            self.season = name[len('Season '):]
            self.showName = os.path.basename(os.path.dirname(self.path))
            self.dirName = self.name
            self.istv = True
            self.mtype = 'tv'
        else:
            self.showName = self.name
            self.istv = False
            self.season = -1
            self.mtype = 'movie'

        # Search for jackett here
        if not os.path.dirname(self.path) + '/' == baseDir:
            self.tmdb = TmdbInfo(self.showName, self.mtype)
            self.url = self.tmdb.url
            self.posterUrl = self.tmdb.posterUrl
            if self.istv and not self.tmdb.id == -1:
                self.tmdbtv = TmdbSeasonInfo(self.tmdb.id, self.season)
                if not self.tmdb.url == '':
                    self.url = self.tmdbtv.url
                    self.posterUrl = self.tmdbtv.posterUrl

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

