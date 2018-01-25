# -*- coding: utf-8 -*-
import urllib2,urllib,re,os,sys
from hashlib import md5
import xbmcplugin,xbmcgui,xbmcaddon,xbmc
import simplejson as json
from time import time
import operator

__baseurl__ = 'https://apizpravy.seznam.cz/v1'
_UserAgent_ = 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.3) Gecko/2008092417 Firefox/3.0.3'
addon = xbmcaddon.Addon('plugin.video.seznam.zpravy')
profile = xbmc.translatePath(addon.getAddonInfo('profile'))
__settings__ = xbmcaddon.Addon(id='plugin.video.seznam.zpravy')
home = xbmc.translatePath(__settings__.getAddonInfo('path')).decode("utf-8")
icon = os.path.join(home, 'icon.png')
nexticon = os.path.join(home, 'nextpage.png')
fanart = os.path.join(home, 'fanart.jpg')
scriptname = addon.getAddonInfo('name')
quality_index = int(addon.getSetting('quality'))
quality_settings = ['ask', '240p', '360p', '480p', '720p', '1080p']
live_playlist = os.path.join(home, 'live.m3u8')
LIMIT = 60

MODE_LIST_SHOWS = 1
MODE_LIST_SEASON = 2
MODE_LIST_EPISODES = 3
MODE_VIDEOLINK = 10
MODE_RESOLVE_VIDEOLINK = 11
MODE_LIST_NEXT_EPISODES = 12

reload(sys)
sys.setdefaultencoding('utf8')

def replaceWords(text, word_dic):
    rc = re.compile('|'.join(map(re.escape, word_dic)))
    def translate(match):
        return word_dic[match.group(0)]
    return rc.sub(translate, text)

WORD_DIC = {
'\u00e1': 'á',
'\u00e9': 'é',
'\u00ed': 'í',
'\u00fd': 'ý',
'\u00f3': 'ó',
'\u00fa': 'ú',
'\u016f': 'ů',
'\u011b': 'ě',
'\u0161': 'š',
'\u0165': 'ť',
'\u010d': 'č',
'\u0159': 'ř',
'\u017e': 'ž',
'\u010f': 'ď',
'\u0148': 'ň',
'\u00C0': 'Á',
'\u00c9': 'É',
'\u00cd': 'Í',
'\u00d3': 'Ó',
'\u00da': 'Ú',
'\u016e': 'Ů',
'\u0115': 'Ě',
'\u0160': 'Š',
'\u010c': 'Č',
'\u0158': 'Ř',
'\u0164': 'Ť',
'\u017d': 'Ž',
'\u010e': 'Ď',
'\u0147': 'Ň',
'\\xc3\\xa1': 'á',
'\\xc4\\x97': 'é',
'\\xc3\\xad': 'í',
'\\xc3\\xbd': 'ý',
'\\xc5\\xaf': 'ů',
'\\xc4\\x9b': 'ě',
'\\xc5\\xa1': 'š',
'\\xc5\\xa4': 'ť',
'\\xc4\\x8d': 'č',
'\\xc5\\x99': 'ř',
'\\xc5\\xbe': 'ž',
'\\xc4\\x8f': 'ď',
'\\xc5\\x88': 'ň',
'\\xc5\\xae': 'Ů',
'\\xc4\\x94': 'Ě',
'\\xc5\\xa0': 'Š',
'\\xc4\\x8c': 'Č',
'\\xc5\\x98': 'Ř',
'\\xc5\\xa4': 'Ť',
'\\xc5\\xbd': 'Ž',
'\\xc4\\x8e': 'Ď',
'\\xc5\\x87': 'Ň',
}

REPL_DICT = {
"&nbsp;": " ",
"&amp;" : "&",
"&quot;": "\"",
"&lt;"  : "<",
"&gt;"  : ">",
"\n"    : "",
"\r"    : "",
"</b>"  : "[/B]",
"</div>": "[CR]",
}

def getLS(strid):
    return addon.getLocalizedString(strid)

def notify(msg, timeout=7000):
    xbmc.executebuiltin('Notification(%s, %s, %d, %s)' % (scriptname, msg.encode('utf-8'), timeout, addon.getAddonInfo('icon')))
    log(msg, xbmc.LOGINFO)

def log(msg, level=xbmc.LOGDEBUG):
    if type(msg).__name__ == 'unicode':
        msg = msg.encode('utf-8')
    xbmc.log("[%s] %s" % (scriptname, msg.__str__()), level)

def logDbg(msg):
    log(msg, level=xbmc.LOGDEBUG)

def logErr(msg):
    log(msg, level=xbmc.LOGERROR)

def makeImageUrl(rawurl):
    return 'http:'+rawurl.replace('{width}/{height}', '360/360')

def getJsonDataFromUrl(url, passw=False, hls=False):
    req = urllib2.Request(url)
    req.add_header('User-Agent', _UserAgent_)
    if passw:
        # Password get from here:
        # https://github.com/kodi-czsk/plugin.video.dmd-czech.stream/blob/60e6ff4fee3deabe5216e3d9f4b84fc301491a19/default.py
        # Thanks to Jiri Vyhnalek, creator of stream.cz plugin
        req.add_header('Api-Password', md5('fb5f58a820353bd7095de526253c14fd'+url.split('http://www.stream.cz/API')[1]+str(int(round(int(time())/3600.0/24.0)))).hexdigest())
    response = urllib2.urlopen(req)
    httpdata = response.read()
    response.close()
    if hls:
        return httpdata
    httpdata = replaceWords(httpdata, WORD_DIC)
    return json.loads(httpdata)

def html2text(html):
    rex = re.compile('|'.join(map(re.escape, REPL_DICT)))
    def doReplace(matchobj):
        return REPL_DICT[matchobj.group(0)]
    text = rex.sub(doReplace, html)
    text = re.sub("<b( .*?)*>", "[B]", text)
    text = re.sub("<br( .*?)*>", "[CR]", text)
    text = re.sub("<p( .*?)*>", "[CR]", text)
    text = re.sub("<div( .*?)*>", "[CR]", text)
    text = re.sub("<.*?>", "", text)
    return text

def listContent():
    # Get main list
    addDir(u'Vše', __baseurl__ + '/documenttimelines?service=zpravy', MODE_LIST_SHOWS, icon)
    data = getJsonDataFromUrl(__baseurl__ + '/sections?service=zpravy&visible=true&embedded=layout')
    show_name = []
    for item in data[u'_items']:
        show_name.append(item[u'name'])
        addDir(item[u'name'], __baseurl__ + '/documenttimelines?service=zpravy&maxItems=' + str(LIMIT) + '&itemIds=section_' + item[u'_id'] + '_zpravy&embedded=layout,service,authors,series,content.properties.embeddedDocument.service', MODE_LIST_SHOWS, icon)
    # if-clauses works as failsafe in case API changes
    if u'Výzva' not in show_name:
        addDir(u'Výzva', __baseurl__ + '/documenttimelines?service=zpravy&maxItems=' + str(LIMIT) + '&itemIds=section_5943ae130ed0676f56d916c3_zpravy', MODE_LIST_SHOWS, icon)
    if u'Duel' not in show_name:
        addDir(u'Duel', __baseurl__ + '/documenttimelines?service=zpravy&maxItems=' + str(LIMIT) + '&itemIds=section_5943ae7fe0cf3d6bfb3df94b_zpravy', MODE_LIST_SHOWS, icon)
    if u'Večerní zprávy' not in show_name:
        addDir(u'Večerní zprávy', __baseurl__ + '/documenttimelines?service=zpravy&maxItems=' + str(LIMIT) + '&itemIds=section_5811346fcb2d9825d2c4ee92_zpravy', MODE_LIST_SHOWS, icon)
    del show_name

def listShows(url):
    data = getJsonDataFromUrl(url)
    items = data[u'_items']
    #logDbg(items)
    for item in items:
        logDbg(item[u'title'])
        if u'documents' in item:
            for article in item[u'documents']:
                if article[u'caption']:
                    addDir(article[u'title'], __baseurl__ + '/documents/' + str(article['uid']) + '?embedded=layout,service,authors,series,content.properties.embeddedDocument.service', MODE_LIST_SEASON, 'https:' + article[u'caption'][u'url'], article[u'perex'], info={'date': article[u'dateOfPublication']})
        elif item[u'caption']:
            addDir(item[u'title'], __baseurl__ + '/documents/' + str(item[u'uid']) + '?embedded=layout,service,authors,series,content.properties.embeddedDocument.service', MODE_LIST_SEASON, 'https:' + item[u'caption'][u'url'], item[u'perex'], info={'date': item[u'dateOfPublication']})


def listSeasons(url):
    data = getJsonDataFromUrl(url)
    name = data[u'title']
    stream_url = ''
    imageicon = ''
    title = data[u'captionTitle']
    info = {}
    if u'video' in data[u'caption']:
        stream_url = data[u'caption'][u'video'][u'sdn'] + 'spl,1,https,VOD'
        imageicon = 'https:' + data[u'caption'][u'video'][u'poster'][u'url']
        info = {'duration': data[u'caption'][u'video'][u'videoInfo'][u'durationS'], 'date':data[u'dateOfPublication']}
    elif u'embedUrl' in data[u'caption']:
        # embedded video from stream.cz
        embed_id = str(data[u'caption'][u'embed'])
        streamcz_json = getJsonDataFromUrl('http://www.stream.cz/API/episode_only/' + embed_id, passw=True)
        stream_url = streamcz_json[u'superplaylist'] + 'spl,1,https,VOD'
        imageicon = 'https:' + data[u'caption'][u'url']
        info = {u'date':data[u'dateOfPublication']}
    elif u'liveStreamUrl' in data[u'caption']:
        stream_url = data[u'caption'][u'liveStreamUrl'] + 'spl,1,https,VOD'
        imageicon = 'https:' + data[u'caption'][u'url']
        info={u'date':data[u'dateOfPublication']}
    if quality_index == 0:
        addDir(name, stream_url, MODE_VIDEOLINK, imageicon)
    else:
        addUnresolvedLink(name, stream_url, imageicon, title, info=info)

    for item in data[u'content']:
        prop = item[u'properties']
        if u'media' in prop:
            #logDbg(prop)
            if prop[u'media'] and (u'video' in prop[u'media']):
                name = prop[u'media'][u'title']
                stream_url = prop[u'media'][u'video'][u'sdn'] + 'spl,1,https,VOD'
                imageicon = 'https:' + prop[u'media'][u'video'][u'poster'][u'url']
                title = prop[u'text']
                info={'duration': prop[u'media'][u'video'][u'videoInfo'][u'durationS'], 'date':data[u'dateOfPublication']}
            elif prop[u'media'] and (u'liveStreamUrl' in prop[u'media']):
                name = u'LIVE: ' + prop[u'media'][u'title']
                stream_url = prop[u'media'][u'liveStreamUrl'] + 'spl,1,https,VOD'
                imageicon = 'https:' + prop[u'media'][u'url']
                title = prop[u'media'][u'title']
                info={'date':data[u'dateOfPublication']}
            if quality_index == 0:
                # solution for 'always ask for quality' option
                addDir(name, stream_url, MODE_VIDEOLINK, imageicon)
            else:
                # quality is set in settings
                addUnresolvedLink(name, stream_url, imageicon, title, info=info)

def extract_time(json):
    try:
        # Also convert to int since update_time will be string.  When comparing
        # strings, "10" is smaller than "2".
        logDbg(json)
        return int(json['page']['update_time'])
    except KeyError:
        return 0

def resolveVideoLink(url, name, popis):
    data = getJsonDataFromUrl(url)
    quality = ''
    qualities = []
    try:
        qualities = sorted(data[u'data'][u'mp4'].keys(), key=operator.itemgetter(1), reverse=False)
    except:
        qualities = sorted(data[u'pls'][u'hls'][u'qualities'], key=operator.itemgetter(1), reverse=False)
    if quality_settings[quality_index] in qualities:
        quality = quality_settings[quality_index]
    else:
        try:
            # sort available qualities according desired one
            quality_sorted = quality_settings[quality_index:0:-1]
            quality_sorted += quality_settings[quality_index+1:]
            for hasq in quality_sorted:
                if hasq in qualities:
                    quality = hasq
                    break
        except:
            # something is wrong, set best quality
            quality = qualities[0]
    logDbg("available qualities: {}".format(qualities))
    logDbg("set quality: {}".format(quality))

    liz = xbmcgui.ListItem()
    try:
        # direct link to mp4 file
        liz = xbmcgui.ListItem(path=data[u'data'][u'mp4'][quality][u'url'], iconImage="DefaultVideo.png")
    except:
        # LIVE video
        liveVideo(data)
        liz = xbmcgui.ListItem(path=live_playlist, iconImage="DefaultVideo.png")
        #liz.setProperty('inputstreamaddon', 'inputstream.adaptive')
        #liz.setProperty('inputstream.adaptive.manifest_type', 'hls')
        liz.setMimeType('application/vnd.apple.mpegurl')
        liz.setContentLookup(False)

    liz.setInfo(type="Video", infoLabels={"Title": name, "Plot": popis})
    liz.setProperty('IsPlayable', 'true')
    liz.setProperty("icon", thumb)
    xbmcplugin.setResolvedUrl(handle=addonHandle, succeeded=True, listitem=liz)

def liveVideo(data):
    live_url = data[u'pls'][u'hls'][u'url']
    live_url = re.sub(r'\bVOD\b', 'EVENT', live_url)
    logDbg('Live URL: ' + str(live_url))
    hls = getJsonDataFromUrl(live_url, hls=True)
    # create local m3u8 playlist
    f = open(live_playlist, 'w')
    f.write(hls)
    f.close()
    f = open(live_playlist, 'r')
    content = ''
    # get base url
    live_url = re.sub(r'\d+\?.*', '', live_url)
    logDbg('Live URL - trimmed: ' + str(live_url))
    for line in f:
        if re.match(r'^#', line):
            line = re.sub(r'(.*)(PROGRAM-ID=.*)(BANDWIDTH.*)', r'\1\3', line)
            content += line
        else:
            # transform relative url to absolute
            content += live_url+line
    f.close()
    # rewrite m3u8 file
    f = open(live_playlist, 'w')
    f.write(content)
    f.close()

def selectQuality(url, name):
    data = getJsonDataFromUrl(url)
    qualities = ''
    try:
        qualities = data[u'data'][u'mp4']
    except:
        qualities = False

    def createOrderedList(data, quality):
        logDbg('Quality - always ask: ' + quality)
        try:
            stream_url = data[u'data'][u'mp4'][quality][u'url']
            liz = xbmcgui.ListItem(quality, iconImage="DefaultVideo.png")
            liz.setProperty('Fanart_Image', fanart)
            xbmcplugin.addDirectoryItem(handle=addonHandle, url=stream_url, listitem=liz)
        except:
            pass

    if not qualities:
        # live video
        liveVideo(data)
        liz = xbmcgui.ListItem(name, path=live_playlist, iconImage="DefaultVideo.png")
        liz.setInfo(type="Video", infoLabels={"Title": name})
        liz.setProperty('isPlayable', 'True')
        xbmcplugin.addDirectoryItem(handle=addonHandle, url=live_playlist, listitem=liz)
    else:
        # order quality heighest -> lowest
        if '1080p' in qualities:
            createOrderedList(data, '1080p')
        if '720p' in qualities:
            createOrderedList(data, '720p')
        if '480p' in qualities:
            createOrderedList(data, '480p')
        if '360p' in qualities:
            createOrderedList(data, '360p')
        if '240p' in qualities:
            createOrderedList(data, '240p')

def getParams():
    param = []
    paramstring = sys.argv[2]
    if len(paramstring) >= 2:
        params = sys.argv[2]
        cleanedparams = params.replace('?', '')
        if (params[len(params)-1] == '/'):
            params = params[0:len(params)-2]
        pairsofparams = cleanedparams.split('&')
        param = {}
        for i in range(len(pairsofparams)):
            splitparams = {}
            splitparams = pairsofparams[i].split('=')
            if (len(splitparams)) == 2:
                param[splitparams[0]] = splitparams[1]
    return param

def composePluginUrl(url, mode, name, plot):
    return sys.argv[0]+"?url="+urllib.quote_plus(url.encode('utf-8'))+"&mode="+str(mode)+"&name="+urllib.quote_plus(name.encode('utf-8'))+'&plot='+urllib.quote_plus(plot.encode('utf-8'))

def addItem(name, url, mode, iconimage, desc, isfolder, islatest=False, info={}):
    u = composePluginUrl(url, mode, name, desc)
    ok = True
    liz = xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=iconimage)
    liz.setInfo(type="Video", infoLabels={"Title": name, "Plot": desc})
    if u'date' in info:
        liz.setInfo('video', {'date': info[u'date'], 'aired': info[u'date'], 'premiered': info[u'date'], 'dateadded': info[u'date']})
    if u'duration' in info:
        liz.addStreamInfo('video', {'duration': info[u'duration']})
    if iconimage:
        liz.setProperty("Fanart_Image", iconimage)
    else:
        liz.setProperty("Fanart_Image", fanart)
    if not isfolder:
        liz.setProperty("IsPlayable", "true")
        menuitems = []
        if islatest:
            next_url = composePluginUrl(url, MODE_LIST_NEXT_EPISODES, name, plot)
            menuitems.append((getLS(30004).encode('utf-8'), 'XBMC.Container.Update('+next_url+')'))
        if quality_index != 0:
            # create custom context menu item
            select_quality_url = composePluginUrl(url, MODE_VIDEOLINK, name, plot)
            menuitems.append((getLS(30005).encode('utf-8'), 'XBMC.Container.Update('+select_quality_url+')'))
        liz.addContextMenuItems(menuitems)
    ok = xbmcplugin.addDirectoryItem(handle=addonHandle, url=u, listitem=liz, isFolder=isfolder)
    return ok

def addDir(name, url, mode, iconimage, plot='', info={}):
    logDbg("addDir(): '"+name+"' url='"+url+"' icon='"+iconimage+"' mode='"+str(mode)+"'")
    return addItem(name, url, mode, iconimage, plot, True)

def addUnresolvedLink(name, url, iconimage, plot='', islatest=False, info={}):
    mode = MODE_RESOLVE_VIDEOLINK
    logDbg("addUnresolvedLink(): '"+name+"' url='"+url+"' icon='"+iconimage+"' mode='"+str(mode)+"'")
    return addItem(name, url, mode, iconimage, plot, False, islatest, info)



addonHandle = int(sys.argv[1])
params = getParams()
url = None
name = None
thumb = None
mode = None
plot = ''

try:
    url = urllib.unquote_plus(params["url"])
except:
    pass
try:
    name = urllib.unquote_plus(params["name"])
except:
    pass
try:
    plot = urllib.unquote_plus(params["plot"])
except:
    pass
try:
    mode = int(params["mode"])
except:
    pass

logDbg("Mode: "+str(mode))
logDbg("URL: "+str(url))
logDbg("Name: "+str(name))
logDbg("Plot: "+str(plot))

if mode == None or url == None or len(url) < 1:
    logDbg('listContent()')
    listContent()

elif mode == MODE_LIST_SHOWS:
    if url:
        logDbg('listShows() with url ' + str(url))
        listShows(url)

elif mode == MODE_LIST_SEASON:
    if url:
        logDbg('listSeasons() with url ' + str(url))
        listSeasons(url)

elif mode == MODE_LIST_EPISODES:
    logDbg('listEpisodes() with url ' + str(url))
    listEpisodes(url)

elif mode == MODE_VIDEOLINK:
    if url:
        logDbg('selectQuality() with url ' + str(url))
        selectQuality(url, name)

elif mode == MODE_RESOLVE_VIDEOLINK:
    logDbg('resolveVideoLink() with url ' + str(url))
    resolveVideoLink(url, name, plot)

elif mode == MODE_LIST_NEXT_EPISODES:
    logDbg('listNextEpisodes() with url ' + str(url))
    listNextEpisodes(url)

xbmcplugin.endOfDirectory(addonHandle)
