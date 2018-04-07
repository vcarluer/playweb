import re
import logging
import urllib
import os
from string import Template
import requests
import json
from flask import Flask, render_template, abort
app = Flask(__name__)

logging.getLogger().setLevel(logging.DEBUG)
baseDir = 'static/ms/'

@app.route('/')
def root():
    return directory(baseDir)

@app.route('/<key>')
def directory(key):
    if key == 'favicon.ico':
        abort(404)

    dirPath = getPath(key)
    dirInfo = DirectoryInfo(dirPath, hd=True)
    if len(dirInfo.movies) == 1:
        return info(dirInfo.movies[0].key)
    else:
        return render_template('movies.html', info=dirInfo.info, dirs=dirInfo.directories, movies=dirInfo.movies)

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
    def __init__(self, path, hd=False):
        self.directories = []
        self.movies = []
        self.name = os.path.basename(path)
        self.path = path
        self.key = getKey(path)
        self.info = DirectoryItem(self.name, self.path, hd)

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
        self.dirPath = os.path.dirname(self.path)
        extsplit = os.path.splitext(self.fileName)
        self.name = os.path.basename(os.path.dirname(self.path))
        self.fileName = extsplit[0]
        self.ext = extsplit[1]
        self.info = DirectoryItem(self.name, self.dirPath, hd=True)
        if self.info.istv:
            self.name = self.getEpisodeName()
        # Subtitles here
        self.subtitles = self.getSubtitles(self.dirPath)
        # Other movie infos
        self.url = self.info.url
        self.posterUrl = self.info.posterUrl

    def getEpisodeName(self):
        p = re.compile('.* - S(\d\d)E(\d\d) - .*')
        m = p.match(self.fileName)
        self.episode = int(m.group(2))
        app.logger.debug('Episode for ' + self.fileName + ' is ' + str(self.episode))
        return self.info.tmdbtv.tmdb['episodes'][self.episode - 1]['name']

    def getSubtitles(self, dirPath):
        subtitles = []
        movieDirFiles = os.listdir(dirPath)
        app.logger.debug('Number of files in movie dir:' + str(len(movieDirFiles)))
        for movieFile in movieDirFiles:
            mfPath = dirPath+ '/' + movieFile
            urlPath = '/' + mfPath
            if os.path.isfile(mfPath):
                app.logger.debug('Handling file: ' + mfPath)
                extsplit = os.path.splitext(movieFile)
                if len(extsplit) > 1:
                    ext = extsplit[1]
                    app.logger.debug('Handling extension: ' + ext)
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
                        app.logger.debug('Adding subtitle ' + subLabel + ': ' + subPath)
                        subtitles.append(subtitle)

        return subtitles

def getposterw(hd):
    if hd:
        '''
"poster_sizes": [
  "w92",
  "w154",
  "w185",
  "w342",
  "w500",
  "w780",
  "original"
]
        '''
        return 780
    else:
        return 185

class TmdbInfo():
    tmdbapi = '372020cd232e0239905b1b2ad473c208'
    searchUrl = Template('https://api.themoviedb.org/3/search/$mtype?api_key=$apikey&query=$query')
    posterUrl = Template('https://image.tmdb.org/t/p/w$width$poster')
    mediaUrl = Template('https://www.themoviedb.org/$mtype/$tmdbid')

    def __init__(self, name, mtype = 'movie', hd=False):
        self.mtype = mtype
        self.origName = name
        self.posterw = getposterw(hd)
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
            self.posterUrl = TmdbInfo.posterUrl.substitute(poster=self.poster, width=self.posterw)
            app.logger.debug('setting poster url to ' + self.posterUrl)
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

    def __init__(self, tvid, season, hd=False):
        self.tvid = tvid
        self.season = season
        self.posterw = getposterw(hd)
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
            self.posterUrl = TmdbInfo.posterUrl.substitute(poster=self.poster, width=self.posterw)
            app.logger.debug('setting season poster url to ' + self.posterUrl)
        else:
            self.posterUrl = ''

class DirectoryItem():
    def __init__(self, name, path, hd=False):
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
            self.season = -1
            self.istv = False
            self.mtype = 'movie'
            for subdir in os.listdir(self.path):
                if subdir.startswith('Season '):
                    self.istv = True
                    self.mtype = 'tv'
                    break

        # Search for jackett here
        if not os.path.dirname(self.path) + '/' == baseDir:
            self.tmdb = TmdbInfo(self.showName, self.mtype, hd)
            self.url = self.tmdb.url
            self.posterUrl = self.tmdb.posterUrl
            if not self.season == -1:
                self.tmdbtv = TmdbSeasonInfo(self.tmdb.id, self.season, hd)
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

