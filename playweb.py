import logging
import urllib
import os
from flask import Flask, render_template
app = Flask(__name__)

logging.getLogger().setLevel(logging.DEBUG)
baseDir = 'static/ms/'

@app.route('/')
def root():
    return movies(baseDir)

@app.route('/<key>')
def movies(key):
    moviePath = urllib.parse.unquote(key.replace('_-', '/'))

    movieDirs = os.listdir(moviePath)
    movies = []
    for movieDir in movieDirs:
        movie = Movie(moviePath + '/' + movieDir, True)
        movies.append(movie)

    return render_template('movies.html', movies=movies)

@app.route('/video/<key>')
def movie(key):
    moviePath = urllib.parse.unquote(key.replace('_-', '/'))
    movie = Movie(moviePath, expand=True)
    app.logger.debug('rendering template video for: ' + movie.videoPath)
    return render_template('video.html', movie=movie)

class Movie():
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

class Subtitle:
    def __init__(self, path, label, default, lang):
        self.path = path
        self.label = label
        self.default = default
        self.lang = lang

