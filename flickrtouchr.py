#!/usr/bin/env python

#
# FlickrTouchr - a simple python script to grab all your photos from flickr,
#                dump into a directory - organised into folders by set -
#                along with any favourites you have saved.
#
#                You can then sync the photos to an iPod touch.
#
# Version:       1.2
#
# Original Author:	colm - AT - allcosts.net  - Colm MacCarthaigh - 2008-01-21
#
# Modified by:			Dan Benjamin - http://hivelogic.com
#
# License:       		Apache 2.0 - http://www.apache.org/licenses/LICENSE-2.0.html
#

import xml.dom.minidom
import webbrowser
import urlparse
import urllib2
import unicodedata
import cPickle
import hashlib
import time
import sys
import os
import argparse
import logging
import xmltodict, json

API_KEY       = "e224418b91b4af4e8cdb0564716fa9bd"
SHARED_SECRET = "7cddb9c9716501a0"

#
# Utility functions for dealing with flickr authentication
#
def getText(nodelist):
    rc = ""
    for node in nodelist:
        if node.nodeType == node.TEXT_NODE:
            rc = rc + node.data
    return rc.encode("utf-8")

#
# Get the frob based on our API_KEY and shared secret
#
def getfrob():
    # Create our signing string
    string = SHARED_SECRET + "api_key" + API_KEY + "methodflickr.auth.getFrob"
    hash   = hashlib.md5(string).hexdigest()

    # Formulate the request
    url    = "https://api.flickr.com/services/rest/?method=flickr.auth.getFrob"
    url   += "&api_key=" + API_KEY + "&api_sig=" + hash

    try:
        # Make the request and extract the frob
        response = urllib2.urlopen(url)

        # Parse the XML
        dom = xml.dom.minidom.parse(response)

        # get the frob
        frob = getText(dom.getElementsByTagName("frob")[0].childNodes)

        # Free the DOM
        dom.unlink()

        # Return the frob
        return frob

    except:
        raise Exception("Could not retrieve frob")

#
# Login and get a token
#
def froblogin(frob, perms):
    string = SHARED_SECRET + "api_key" + API_KEY + "frob" + frob + "perms" + perms
    hash   = hashlib.md5(string).hexdigest()

    # Formulate the request
    url    = "https://api.flickr.com/services/auth/?"
    url   += "api_key=" + API_KEY + "&perms=" + perms
    url   += "&frob=" + frob + "&api_sig=" + hash

    # Tell the user what's happening
    print "In order to allow FlickrTouchr to read your photos and favourites"
    print "you need to allow the application. Please press return when you've"
    print "granted access at the following url (which should have opened"
    print "automatically)."
    print
    print url
    print
    print "Waiting for you to press return"

    # We now have a login url, open it in a web-browser
    webbrowser.open_new(url)

    # Wait for input
    sys.stdin.readline()

    # Now, try and retrieve a token
    string = SHARED_SECRET + "api_key" + API_KEY + "frob" + frob + "methodflickr.auth.getToken"
    hash   = hashlib.md5(string).hexdigest()

    # Formulate the request
    url    = "https://api.flickr.com/services/rest/?method=flickr.auth.getToken"
    url   += "&api_key=" + API_KEY + "&frob=" + frob
    url   += "&api_sig=" + hash

    # See if we get a token
    try:
        # Make the request and extract the frob
        response = urllib2.urlopen(url)

        # Parse the XML
        dom = xml.dom.minidom.parse(response)

        # get the token and user-id
        token = getText(dom.getElementsByTagName("token")[0].childNodes)
        nsid  = dom.getElementsByTagName("user")[0].getAttribute("nsid")

        # Free the DOM
        dom.unlink()

        # Return the token and userid
        return (nsid, token)
    except:
        raise Exception("Login failed")

#
# Sign an arbitrary flickr request with a token
#
def flickrsign(url, token):
    query  = urlparse.urlparse(url).query
    query += "&api_key=" + API_KEY + "&auth_token=" + token
    params = query.split('&')

    # Create the string to hash
    string = SHARED_SECRET

    # Sort the arguments alphabettically
    params.sort()
    for param in params:
        string += param.replace('=', '')
    hash   = hashlib.md5(string).hexdigest()

    # Now, append the api_key, and the api_sig args
    url += "&api_key=" + API_KEY + "&auth_token=" + token + "&api_sig=" + hash

    # Return the signed url
    return url

#
# Print photo details
#
def getphotometa(photoid):
    detailurl   = "https://api.flickr.com/services/rest/?method=flickr.photos.getInfo&photo_id=" + photoid

	# Sign the url
    request = flickrsign(detailurl, config["token"])

	# Make the request
    response = urllib2.urlopen(request)
    return xmltodict.parse(response, cdata_key='text', attr_prefix='')['rsp']['photo']

#
# Grab the photo from the server
#
def getphoto(imgurl, filename):
    try:
        response = urllib2.urlopen(imgurl)
        data = response.read()

        # Save the file!
        fh = open(filename, "wb")
        fh.write(data)
        fh.close()

        return filename
    except Exception as e:
        print 'ERROR: Download ' + imgurl + ' to ' + filename
        logger.error(e)

######## Main Application ##########
if __name__ == '__main__':


    # parse arguments
    try:
        parser = argparse.ArgumentParser(prog='python flickrtouchr.py')
        parser.add_argument("dir", help='root output directory')
        parser.add_argument("-p", "--prefix", default="%Y/%m", help='prefix dirs by datetaken (default: %%Y/%%m)')
        parser.add_argument("-s", "--skipsets", default=False, action='store_true', help='skip the photo sets names in structure')
        parser.add_argument("-m", "--metadata", default=False, action='store_true', help='save photo metadata in json (slower)')
        parser.add_argument("-f", "--favorites", default=False, action='store_true', help="download also favorites")
        parser.add_argument("-l", "--log", default="WARNING", choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], help="Set the logging level")

        args = parser.parse_args()
    except:
        sys.exit(1)

    # The first, and only argument needs to be a directory
    try:
        os.chdir(args.dir)
    except:
        parser.print_help()
        sys.exit(1)

    logging.basicConfig(filename='flickr.log', level=args.log, format='%(asctime)s %(levelname)s %(message)s')
    logger = logging.getLogger(__name__)

    # First things first, see if we have a cached user and auth-token
    try:
        cache = open("touchr.frob.cache", "r")
        config = cPickle.load(cache)
        cache.close()

    # We don't - get a new one
    except:
        (user, token) = froblogin(getfrob(), "read")
        config = { "version":1 , "user":user, "token":token }

        # Save it for future use
        cache = open("touchr.frob.cache", "w")
        cPickle.dump(config, cache)
        cache.close()

    # Now, construct a query for the list of photo sets
    url  = "https://api.flickr.com/services/rest/?method=flickr.photosets.getList"
    url += "&user_id=" + config["user"]
    url  = flickrsign(url, config["token"])

    # get the result
    response = urllib2.urlopen(url)

    # Parse the XML
    dom = xml.dom.minidom.parse(response)

    # Get the list of Sets
    sets =  dom.getElementsByTagName("photoset")

    # For each set - create a url
    print str(sets.length) + ' photo sets for processing...'
    urls = []
    for set in sets:
        pid = set.getAttribute("id")
        dir = getText(set.getElementsByTagName("title")[0].childNodes)
        dir = unicodedata.normalize('NFKD', dir.decode("utf-8", "ignore")).encode('ASCII', 'ignore') # Normalize to ASCII

        # Build the list of photos
        # see https://www.flickr.com/services/api/flickr.photosets.getPhotos.html
        url   = "https://api.flickr.com/services/rest/?method=flickr.photosets.getPhotos"
        url  += "&extras=date_taken,url_o,original_format,geo"
        url  += "&photoset_id=" + pid

        # Append to our list of urls
        urls.append( (url , dir) )

    # Free the DOM memory
    dom.unlink()

    # Add the photos which are not in any set
    url  = "https://api.flickr.com/services/rest/?method=flickr.photos.getNotInSet"
    url += "&extras=date_taken,url_o,original_format,geo"
    urls.append((url, 'No Set'))

    # Add the user's Favourites
    if args.favorites:
        url   = "https://api.flickr.com/services/rest/?method=flickr.favorites.getList"
        url += "&extras=date_taken,url_o,original_format,geo"
        urls.append((url, 'F-A-V-O-R-I-T-E-S'))

    # Time to get the photos
    print 'Prepare photos to download...'

    download = 0
    skip = 0
    inodes = {}
    for (url , dir) in urls:

        # Get 500 results per page
        url += "&per_page=500"
        pages = page = 1

        while page <= pages:
            request = url + "&page=" + str(page)

            # Sign the url
            request = flickrsign(request, config["token"])

            # Make the request
            response = urllib2.urlopen(request)

            # Parse the XML
            dom = xml.dom.minidom.parse(response)

            # Get the total
            try:
                pages = int(dom.getElementsByTagName("photo")[0].parentNode.getAttribute("pages"))
            except IndexError:
                pages = 0


            # Grab the photos
            for photo in dom.getElementsByTagName("photo"):
                # Grab the id, datetaken, original url
                photoid = photo.getAttribute("id").encode("utf8")
                originalurl = photo.getAttribute('url_o').encode("utf8")
                datetaken = time.strptime(photo.getAttribute('datetaken').encode("utf8"), '%Y-%m-%d %H:%M:%S')
                media = photo.getAttribute('media').encode("utf8")
                originalformat = photo.getAttribute('originalformat').encode("utf8")

                # some images don't have originalurl
                if not originalurl:
                    logger.debug('Image id=' + photoid + ' originalurl missing')
                    continue

                # Decide about grabbing structure
                fulldir = ''
                if args.prefix:fulldir = time.strftime(args.prefix, datetaken)
                if not args.skipsets: fulldir = fulldir + '/' + dir
                if dir == 'F-A-V-O-R-I-T-E-S': fulldir = 'Favourites'

                # Create the directory if not exists
                if not os.path.isdir(fulldir): os.makedirs(fulldir)

                # target photo, video
                target = fulldir + "/" + photoid + "." + originalformat

                # Skip videos (not supported now)
                if media == 'video':
                    logger.debug('Video id=' + photoid + ' ' + originalurl  + ' => ' + target + " ")
                    continue

                # Skip files that exist
                if os.access(target, os.R_OK):
                    inodes[photoid] = target
                    skip = skip +1
                    logger.debug('photo ' + originalurl  + ' => ' + target + " already exitst")
                else:
                    # Save metadata about file to json
                    metadata = fulldir + '/.' + photoid + ".json"
                    if args.metadata:
                        with open(metadata, "wb") as outfile:
                            json.dump(getphotometa(photoid), outfile, indent=2)

                    # Look it up in our dictionary of inodes first
                    if photoid in inodes and inodes[photoid] and os.access(inodes[photoid], os.R_OK):
                        # woo, we have it already, use a hard-link
                        os.link(inodes[photoid], target)
                    else:
                        # download photo and increase counter
                        inodes[photoid] = getphoto(originalurl, target)
                        download = download + 1
                        logger.debug('download ' + originalurl  + ' => ' + target)

                sys.stdout.write("Download %d images. Skip %d existing images...\r" % (download, skip))
                sys.stdout.flush()

            # Move on the next page
            page = page + 1
