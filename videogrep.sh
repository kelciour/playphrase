#!/bin/bash

media_dir="/media/nickolay/9A043D5E043D3F17/English Movies"

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
        python "playphrase.py" --input "$media_dir" "$phrase"
    fi
done
