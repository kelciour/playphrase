#!/bin/bash

media_dir="/media/nickolay/9A043D5E043D3F17/English AudioBooks"

while true
do
    read -p "Phrase: " -r phrase
    if [ "$phrase" = "q" ]; then
        exit 0
    elif [ "$phrase" = "x" ]; then
        exit 0
    elif [ "$phrase" = "quit" ]; then
        exit 0
    elif [ "$phrase" = "exit" ]; then
        exit 0
    else    
        # Disable album cover art and create a window even if there is no album cover art.
        # python "playphrase.py" --mpv-options "--video=no --force-window=yes --osc=no --title=${filename}" --input "$media_dir" "$phrase"

        python "playphrase.py" --mpv-options "--sub-font-size=37 --sub-back-color=0.05/0.9 --sub-scale-by-window=no --sub-scale-with-window=no --autofit=620 --osc=no --title=${filename}" --input "$media_dir" "$phrase"
    fi
done
