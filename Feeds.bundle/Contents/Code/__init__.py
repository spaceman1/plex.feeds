from PMS import *
from PMS.Objects import *
from PMS.Shortcuts import *

import re, string, pickle, os, urllib

from lxml import html

PLUGIN_PREFIX = '/video/feeds'

DAY = 86400
CACHE_TIME = DAY

# TODO: Find double posts and take only the last one
# TODO: Add remove feed and remove item menus
# TODO: Add option for media pre-caching
# TODO: Add import from iTunes podcasts
# TODO: Remember items after they disappear from the feed
# TODO: Generic icons for audio/video
# TODO: Handle no existing Feeds folder

####################################################################################################

def Start():
  Plugin.AddPrefixHandler(PLUGIN_PREFIX, MainMenu, L('Feeds'), 'icon-default.gif', 'art-default.jpg')
  
  Plugin.AddViewGroup('Details', viewMode='InfoList', mediaType='items')
  Plugin.AddViewGroup('EpisodeList', viewMode='Episodes', mediaType='items')
  
  MediaContainer.title1 = L('Feeds')
  MediaContainer.viewGroup = 'Details'
  MediaContainer.art = R('art-default.jpg')
  
  HTTP.SetCacheTime(CACHE_TIME)
    
####################################################################################################

def CreatePrefs():
  addPref('feeds', dict(), dict(), L('Feeds'))
  addPref('rolls', list(), list(), L('Feedrolls'))

####################################################################################################

def MainMenu():  
  dir = MediaContainer()
  dir.nocache = 1
  
  feeds = getFeedsFromFiles()
  knownFeeds = getPref('feeds')
  for feedKey in feeds.iterkeys():
    if feedKey not in knownFeeds:
      knownFeeds[feedKey] = feeds[feedKey]
  
  knownFeedList = sorted(knownFeeds.iteritems(), key=lambda x: x[1]['title'])

  for feed in knownFeedList:
    if feed[1]['enabled']:
      dir.Append(Function(DirectoryItem(feedMenu, title=feed[1]['title'], summary=feed[1]['summary'], thumb=feed[1]['thumb']), key=feed[0]))
  
  dir.Append(Function(DirectoryItem(settingsMenu, title=L('Settings'))))
  return dir
  
def feedMenu(sender, key):
  dir = MediaContainer()
  Log(sender.itemTitle)
  dir.title2 = sender.itemTitle
  
  feedContents = HTTP.Request(key)
  for item in XML.ElementFromString(feedContents).xpath('/rss/channel/item'):
    title = item.xpath('child::title')[0].text

    try:    
      description = item.xpath('child::description')[0].text
    except:
      description = ''
    try:
      # Some people insist on putting html in description tags
      descriptionHTML = html.fragment_fromstring(description)
      description = html.tostring(descriptionHTML, method="text").strip()
    except: pass

    try:
      url = item.xpath('child::enclosure')[0].get('url')
      foundURL = True
    except: foundURL = False
            
    if not foundURL:
      try:
        url = item.xpath('child::*[name()="media:content"]')[0].get('url')
        foundURL = True
      except: pass
      
    if not foundURL:
      try:
        
        for elem in item.xpath('child::*[name()="media:group"]')[0].xpath('child::*[name()="media:content"]'):
          elemURL = elem.get('url')
          if getType(elemURL) != None:
            url = elemURL
            foundURL = True
      except: pass
    
    if not foundURL:
      try: 
        url = item.xpath('child::link')[0].text
        foundURL = True
      except: pass
          
    if foundURL:
      Log(url)
        
      try:
        duration = item.xpath('child::duration')[0].text
        durationPartCount = duration.count(":")
        if durationPartCount == 2:
          (hours, minutes, seconds) = duration.split(':')
          duration = int(hours) * 3600 + int(minutes) * 60 + int(seconds)
        elif durationPartCount == 1:
          (minutes, seconds) = duration.split(':')
          duration = int(minutes) * 60 + int(seconds)
        else:
            duration = int(duration)
      except:
        duration = ""
    
      dir.Append(initURL(url, title=title, summary=description, duration=duration))
  return dir

####################################################################################################

def settingsMenu(sender):
  dir = MediaContainer(title2=L('Settings'))
  dir.Append(Function(DirectoryItem(addFeeds, title=L('Add Feeds'))))
  dir.Append(Function(DirectoryItem(removeFeeds, title=L('Remove Feeds'))))
  dir.Append(Function(SearchDirectoryItem(addFeedRollURL, title=L('Add Feedroll'), prompt=L('Enter feedroll address'))))
  dir.Append(Function(DirectoryItem(removeRolls, title=L('Remove Feedroll'))))
  dir.Append(Function(DirectoryItem(removeMedia, title=L('Remove Media'))))
  return dir
  
def addFeeds(sender):
  dir = MediaContainer(title2=L('Add Feeds'))
  dir.Append(Function(SearchDirectoryItem(addFeedURL, title=L('Add Feed'), prompt=L('Enter feed address'))))
  return dir
      
def addFeedURL(sender, query):
  feedContents = HTTP.Request(query)
  newFeed = getFeedMetaData(feedContents)
  Log(newFeed)
  knownFeeds = getPref('feeds')
  if newFeed['key'] not in knownFeeds:
    knownFeeds[feed['key']] = newFeed
    setPref('feeds', knowFeeds)
  return

def addFeedRollURL(sender, query):
  Log('addFeedRollURL called')
  knownFeeds = getPref('feeds')
  knownRolls = getPref('rolls')
  if query not in knownRolls:
    knownRolls.append(query)
    setPref('rolls', knownRolls)
    
  newFeeds = getFeeds(query)
  shouldSetPref = False
  for newFeed in newFeeds:
    if newFeed['key'] not in knownFeeds:
      knownFeeds[feed['key']] = newFeed
      shouldSetPref = True
  
  if shouldSetPref: setPref('feeds', knowFeeds)
  return

def removeRolls(sender):
  pass
  
def removeFeeds(sender):
  pass
  
def removeMedia(sender):
  pass

####################################################################################################

def getFeedsFromFiles():
  dataDir = Data.__dataPath + '/Feeds'
  feeds = dict()
  for dataFile in os.listdir(dataDir):
    if dataFile != '.DS_Store' and os.path.isfile(dataDir + '/' + dataFile):
      newFeeds = getFeeds('file://' + urllib.pathname2url(dataDir + '/' + dataFile))
      for newFeed in newFeeds:
        feeds[newFeed['key']] = newFeed['data']
  return feeds

def getFeeds(url):
  (name, ext) = os.path.splitext(url)
  groupContents = HTTP.Request(url)
  newFeeds = list()
  Log(ext)
  if ext == '.xml' or ext == '.rss':
    for feed in XML.ElementFromString(groupContents).xpath('/rss/channel/item/link'):   
      feedURL = feed.text
      try:
        feedContents = HTTP.Request(feedURL)
        feedData = getFeedMetaData(feedContents)
        newFeeds.append(dict(key=feedURL, data=feedData))
      except: Log("Couldn't open " + feedURL)
  elif ext == '.opml':
    for feed in XML.ElementFromString(groupContents).xpath('/opml/body/outline'):
      feedURL = feed.get('xmlUrl')
      try:
        feedContents = HTTP.Request(feedURL)
        feedData = getFeedMetaData(feedContents)
        newFeeds.append(dict(key=feedURL, data=feedData))
      except: Log("Couldn't open " + feedURL)
  else:
    for feedURL in groupContents.split('\n'):
      try:
        feedContents = HTTP.Request(feedURL)
        feedData = getFeedMetaData(feedContents)
        newFeeds.append(dict(key=feedURL, data=feedData))
      except: Log("Couldn't open " + feedURL)
  return newFeeds

def getFeedMetaData(feedContents):
  title = XML.ElementFromString(feedContents).xpath('/rss/channel/title')[0].text
  try:
    description = XML.ElementFromString(feedContents).xpath('/rss/channel/description')[0].text
  except:
    description = ''
  try:
    image = XML.ElementFromString(feedContents).xpath('/rss/channel/image/url')[0].text
  except:
    image = ''
  return dict(title=title, summary=description, thumb=image, enabled=True)

####################################################################################################  

def getType(url):
  # Types from http://xbmc.org/wiki/?title=Advancedsettings.xml
  # echo $1 | tr ' ' '\n' | sed "s/\(.*\)/'\1',/" | tr '\n' ' '
  if url.endswith('.wmv'):
    return None # removed due to ffmpeg issue in Plex
  if url.endswith(('.m4v', '.3gp', '.nsv', '.ts', '.ty', '.strm', '.rm', '.rmvb', '.m3u', '.ifo', '.mov', '.qt', '.divx', '.xvid', '.bivx', '.vob', '.nrg', '.img', '.iso', '.pva', '.asf', '.asx', '.ogm', '.m2v', '.avi', '.bin', '.dat', '.dvr-ms', '.mpg', '.mpeg', '.mp4', '.mkv', '.avc', '.vp3', '.svq3', '.nuv', '.viv', '.dv', '.fli', '.flv', '.rar', '.001', '.wpl', '.zip')):
    return VideoItem
  if url.endswith(('.nsv', '.m4a', '.flac', '.aac', '.strm', '.pls', '.rm', '.mpa', '.wav', '.wma', '.ogg', '.mp3', '.mp2', '.m3u', '.mod', '.amf', '.669', '.dmf', '.dsm', '.far', '.gdm', '.imf', '.it', '.m15', '.med', '.okt', '.s3m', '.stm', '.sfx', '.ult', '.uni', '.xm', '.sid', '.ac3', '.dts', '.cue', '.aif', '.aiff', '.wpl', '.ape', '.mac', '.mpc', '.mp+', '.mpp', '.shn', '.zip', '.rar', '.wv', '.nsf', '.spc', '.gym', '.adplug', '.adx', '.dsp', '.adp', '.ymf', '.ast', '.afc', '.hps', '.xsp')):
    return TrackItem
    # fla, flv, swt, swc ?
#  if url.endswith(('swf', 'scr')):
  return WebVideoItem
#  return None
  
def initURL(url, title, summary, duration):
  urlType = getType(url)
  if urlType == VideoItem: return VideoItem(url, title=title, summary=summary, duration=duration)
  if urlType == WebVideoItem: return WebVideoItem(url, title=title, summary=summary, duration=duration)
  if urlType == TrackItem: return TrackItem(url, title=title, duration=duration)
####################################################################################################  

def setPref(id, value):
  Prefs.Set(id, pickle.dumps(value))

def getPref(id):
  return pickle.loads(Prefs.Get(id))
  
def addPref(id, kind, default, name):
  Prefs.Add(id, kind, pickle.dumps(default), name)
  
####################################################################################################
