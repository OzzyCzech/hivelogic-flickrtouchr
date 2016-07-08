# Flickr backup

A Python script to grab all your photos from Flickr and dump them into a
directory, organized into folders by set name and year/months.

Original author is [Colm MacCárthaigh](http://www.stdlib.net/~colmmacc/).

Changes include tweaks to download full-size original images and improvements in handling UTF8 file and photoset names.

# Requirements

- download [xmltodic](https://github.com/martinblech/xmltodict) or run `pip install xmltodict`

# Usage

Run it like this:

```
python flickrtouchr.py -h
usage: python flickrtouchr.py [-h] [--prefix PREFIX] [--skipsets] [--metadata]
                              dir

positional arguments:
  dir              root output directory

optional arguments:
  -h, --help       show this help message and exit
  --prefix PREFIX  prefix dirs by datetaken (default: %Y/%m)
  --skipsets       skip the photo sets names in structure
  --metadata       save photo metadata in json (slower)
```

Follow example organize photos in structure `year/month/[photo]` and download also metadata

```
mkdir backup && flickrtouchr.py --metadata --skipsets backup
```

Follow example organize photos in structure `year/month/set/[photo]` and download also metadata

```
mkdir backup && flickrtouchr.py --metadata backup
```

Follow example organize photos in structure `year/[photo]` and download also metadata

```
mkdir backup && flickrtouchr.py --prefix="%Y" --skipsets backup
```

You'll be prompted to authorize with Flickr, and then the magic happens...
