from PMS import *
from PMS.Objects import *
from PMS.Shortcuts import *

from lxml import html

PLUGIN_PREFIX = '/video/feeds'

DAY = 86400
CACHE_TIME = DAY

# TODO: Find double posts and take only the last one
# TODO: Add remove item menus
# TODO: Add option for media pre-caching
# TODO: Add import from iTunes podcasts
# TODO: Remember items after they disappear from the feed
# TODO: Generic icons for audio/video
# TODO: Add UpdateCache()

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
# Boxee: <rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/" xmlns:boxee="as http://boxee.tv/spec/rss/">
# rss/channel
#   title
#   boxee:display
#     boxee:view[@default=<an id in view-option>]
#       boxee:view-option[@id=<type int>][@view-type="line|thumb|thumb-with-preview|defailed-list"]
#     boxee:sort[@default=<an id in sort-option>][@folder-position="start|end|integral"
#       boxee:sort-option[@id=<type int>][sort-by="label|date|episode|none"][sort-order="ascending|descending"][@sort-type-name=<type str>]
#   boxee:expiry # minutes for which this RSS should be cached. 0 means that the RSS should not be cached
#   boxee:background-image
#   
#   item
#     title
#     pubDate # RFC 822
#     link
#     description
#     media:content[@url][@type=<MIME-type>][@duration]
#     media:thumbnail
#     media:credit[@role="actor|director|writer|artist|author"]
#     media:rating[@scheme="urn:mpaa|urn:tv|urn:user"]
#     media:copyright
#     media:keywords # comma-delimited
#     media:category[@scheme="urn:boxee:genre|urn:boxee:title-type|urn:boxee:episode|urn:boxee:season|urn:boxee:show-title|urn:boxee:view-count|urn:boxee:view-count"]
#     boxee:alternative-link[@label|@thumb|@url]


# Yahoo: <rss version="2.0" xmlns:media="http://video.search.yahoo.com/mrss">
# rss/channel/item
#   media:content[@url][@fileSize=<byteCount>][@type=<MIME type>][@medium="image|audio|video|document|executable"][@isDefault="true|false"][@expression="sample|full|nonstop"][@bitrate=<kbps>][@framerate][@samplingrate=<kHz>][@channels][@duration=<seconds>][@height][@width][@lang=<RFC 3066>]
#   media:group
#     media:content # See above
# channel|item|media:content|media:group
#   media:adult
#   media:rating[@scheme="urn:simple|urn:icra|urn:mpaa|urn:vchip"]
#   media:title[@type="plain|html"]
#   media:description[@type="plain|html"]
#   media:keywords
#   media:thumbnail[@url][@height][@width]
#   media:category[@scheme=<url>][@label] # scheme defaults to http://video.search.yahoo.com/mrss/category_schema
#   media:hash[@algo="md5|sha-1"]
#   media:player[@url][@height][@width]
#   media:credit[@role][@scheme] # scheme defaults to urn:ebu
#   media:copyright
#   media:text[@type="plain|html"][@lang][@start][@end]
#   media:restriction[@relationship="allow|deny"][@type="country|uri"] # country is ISO 3166

# iTunes: <rss xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" version="2.0">
# rss/channel
#   ttl: minutes between refreshes. Default 24hr
#   link
#   copyright
#   category
#   itunes:new-feed-url
#   itunes:owner
#     itunes:name
#     itunes:email
#   item
#     pubDate # RFC 2822
#     itunes:pubDate # alternative to pubDate
#     itunes:category
#     itunes:duration # HH:MM:SS or total number of seconds
#     enclosure
#     guid # if omited use url
# channel|item
#   title
#   itunes:author
#   itunes:block
#   itunes:explicit # yes|no|clean # default no
#   itunes:image
#   itunes:keywords
#   itunes:subtitle
#   itunes:summary
#   language
####################################################################################################
def MainMenu():
  dir = MediaContainer()
  dir.nocache = 1
  
  knownFeeds = Data.LoadObject('feeds')
  if knownFeeds == None: knownFeeds = dict()
    
  shouldwritePref = False
    
  feeds = sorted(knownFeeds.iteritems(), key=lambda x: x[1]['title'])
  for feed in feeds:
    if feed[1]['enabled']:
      dir.Append(Function(DirectoryItem(feedMenu, title=feed[1]['title'], summary=feed[1]['summary'], thumb=feed[1]['thumb']), key=feed[0]))
  
  dir.Append(Function(DirectoryItem(settingsMenu, title=L('Settings'))))
  return dir
  
def feedMenu(sender, key):
  dir = MediaContainer(title2=sender.itemTitle, nocache=1)
  
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
  dir.Append(Function(DirectoryItem(removeMedia, title=L('Remove Media'))))
  return dir
  
def addFeeds(sender):
  dir = MediaContainer(title2=L('Add Feeds'))
  dir.Append(Function(SearchDirectoryItem(addFeedURL, title=L('Add Feed'), prompt=L('Enter feed address'))))
  return dir
      
def addFeedURL(sender, query):
  key = String.Unquote(query)
  feedContents = HTTP.Request(key)
  newFeed = getFeedMetaData(feedContents)
  Log(newFeed)
  knownFeeds = Data.LoadObject('feeds')
  if newFeed[key] not in knownFeeds:
    knownFeeds[feed[key]] = newFeed
    Data.SaveObject('feeds', knowFeeds)
  return
  
def removeRoll(sender, key):
  rolls = Data.LoadObject('rolls')
  rolls[key]['enabled'] = False
  Data.SaveObject('rolls', rolls)
  return
  
def removeFeeds(sender):
  dir = MediaContainer(title2=L('Remove Feeds'), nocache=1)
  feeds = Data.LoadObject('feeds')
  feedList = sorted(feeds.iteritems(), key=lambda x: x[1]['title'])
  for feed in feedList:
    if feed[1]['enabled']:
      dir.Append(Function(DirectoryItem(removeFeed, title=feed[1]['title'], summary=feed[1]['summary'], thumb=feed[1]['thumb']), key=feed[0]))
  return dir
  
def removeFeed(sender, key):
  feeds = Data.LoadObject('feeds')
  feeds[key]['enabled'] = False
  Data.SaveObject('feeds', feeds)
  return

def removeMedia(sender):
  pass

####################################################################################################

#def getFeeds(url):
  #### For reference only ####
#  if ext == '.xml' or ext == '.rss':
#    title = XML.ElementFromString(groupContents).xpath('/rss/channel/title')[0].text
#    summary = XML.ElementFromString(groupContents).xpath('/rss/channel/description')[0].text
#    thumb = XML.ElementFromString(groupContents).xpath('/rss/channel/image/url')[0].text
#  elif ext == '.opml':
#    title = XML.ElementFromString(groupContents).xpath('/opml/head/title')[0].text

def getFeedMetaData(feedContents):
  feed = XML.ElementFromString(feedContents)
  title = feed.xpath('/rss/channel/title')[0].text
  try:
    description = feed.xpath('/rss/channel/description')[0].text
  except:
    description = ''
  try:
    image = feed.xpath('/rss/channel/image/url')[0].text
  except:
    image = ''
  try:
    art = feed.xpath('/rss/channel/*[name()="boxee:background-image"]')[0].text
  except:
    art = ''
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
