# PlayPhrase

Search for specific words or phrases in subtitle files and watch video fragments with [mpv](https://mpv.io/).

Inspired by [videogrep](http://lav.io/2014/06/videogrep-automatic-supercuts-with-python/) and [playphrase.me](http://playphrase.me/).

# Video

[![YouTube: PlayPhrase for Movies](http://i.imgur.com/QZ9QSiO.png)](http://youtu.be/ciMEY3moATU)

# Usage

Run ```python playphrase.py -i <media_dir> _init_``` to generate txt files from srt files that will be used for search (only the first time or when you add new movies in your folder).

After that use 
```python playphrase.py -i <media_dir> <phrase>```

Regular expressions can be used in search, for example, \b for word boundary.

### Keyboard Shortcuts 

Use ```Enter``` to move to the next clip or ```Shift + <``` and ```Shift + >``` to switch between clips, ```Ctrl + Left``` and ```Ctrl + Right``` to move to the prev/next subtitle, ```q``` to close video player.

More info: [https://mpv.io/manual/stable/#keyboard-control](https://mpv.io/manual/master/#keyboard-control)

### Batch Scripts

There's ```videogrep.bat``` (Windows) and ```videogrep.sh``` (Linux) files to simplify user input. First time before running edit them and update ```media_dir``` path. Use ```quit```, ```exit``` or ```q```, ```x``` to exit from the batch script.

Here's a quick demo how to set up and run ```videogrep.bat``` on Windows ([YouTube](https://youtu.be/kEkXZY4LFCY)).

### Additional Options:

* ```-ph, --phrases GAP_BETWEEN_PHRASES``` 
move start time of the clip to the beginning of the current phrase. Value is optional (default=1.25 seconds)
* ```-l, --limit``` 
maximum duration of the phrase (default=60 seconds)
* ```-p, --padding``` 
padding in seconds to add to the start and end of each clip (default=0.0 seconds)
* ```-e, --ending``` 
play only matching lines (or phrases)
* ```-r, --randomize``` 
randomize clips
* ```-o, --output``` 
name of the file in which output of \'grep\' command will be written
* ```-d, --demo``` 
only show grep results
* ```-a, --audio```
create audio fragments
* ```-v, --video```
create video fragments
* ```-vs, --video-sub```
create video fragments with hardcoded subtitles
* ```-s, --subtitles```
create subtitles for fragments
* ```-m, --mpv-options OPTIONS```
mpv player options

### Optional Configuration Changes

For example, you can modify [mpv.conf](https://mpv.io/manual/stable/#configuration-files)


```
autofit=900
geometry=50%:50%
```

and [input.conf](https://mpv.io/manual/stable/#interactive-control)


```
ENTER playlist-next force
```

More info: [https://mpv.io/manual/](https://mpv.io/manual/)

# Download

See [https://github.com/kelciour/playphrase/releases](https://github.com/kelciour/playphrase/releases/latest)

# Usage with AudioBooks

It's possible to use audiobooks as media input. For that purpose there's ```audiogrep.bat``` and ```audiogrep.sh``` files to simplify user input. But you need to generate subtitles for every audio file. It can be done almost automatically using [aeneas](https://github.com/readbeyond/aeneas). Also [csplit](https://en.wikipedia.org/wiki/Csplit) can be used to split text of the book by chapters and [Pragmatic Segmenter](https://github.com/diasks2/pragmatic_segmenter) to split chapter's content by "sentences".

Here's example video how it looks like (YouTube):

[![YouTube: PlayPhrase for AudioBooks](http://i.imgur.com/gUFXeVI.png)](https://youtu.be/LEyRfy7TsnE)

# Requirements

* python 2.7
* grep
* mpv
* ffmpeg

# Note

* playphrase requires the subtitle track and the video file to have the exact same name, up to the extension.
