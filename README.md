# videogrep
Search for specific words in srt files and watch with mpv.  
Inspired by [videogrep](http://lav.io/2014/06/videogrep-automatic-supercuts-with-python/) and [playphrase.me](http://playphrase.me/).

# Download

* Windows - [https://github.com/kelciour/playphrase/releases](https://github.com/kelciour/playphrase/releases)
* Linux and MacOS - [playphrase-master.zip](https://github.com/kelciour/playphrase/archive/master.zip)  

# Requirements

* Python 2.7
* grep
* mpv

# Usage

Run ```python videogrep.py -i <media_dir> _init_``` to generate txt files from srt files that will be used for search (only the first time or when you add new movies in your folder).

After that use 
```python videogrep.py -i <media_dir> <phrase>```

### Keyboard Shortcuts 
Use ```Enter``` to move to the next clip or ```Shift + <``` and ```Shift + >``` to switch between clips, ```q``` to close player and ```f``` to toggle fullscreen.

More info: [https://mpv.io/manual/master/#keyboard-control](https://mpv.io/manual/master/#keyboard-control)

###Additional options:
* ```-ph, --phrases GAP_BETWEEN_PHRASES``` 
move start time of the clip to the beginning of the current phrase. Value is optional (default=1.75 seconds)
* ```-l, --limit``` 
maximum duration of the phrase (default=30 seconds)
* ```-p, --padding``` 
padding in seconds to add to the start and end of each clip (default=0.0 seconds)
* ```-e, --ending``` 
play only matching lines (or phrases)
* ```-r, --randomize``` 
randomize the clips
* ```-o, --output``` 
name of the file in which output of \'grep\' command will be written
* ```-d, --demo``` 
only show grep results

# Note

* videogrep requires the subtitle track and the video file to have the exact same name, up to the extension.
* just re-run your command if there was an error with pipe