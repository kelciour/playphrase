#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import sys
import subprocess
import time

movie_extensions = ['mp4', 'avi', 'mkv']

def srt_time_to_seconds(time):
    split_time = time.split(',')
    major, minor = (split_time[0].split(':'), split_time[1])
    return int(major[0]) * 3600 + int(major[1]) * 60 + int(major[2]) + float(minor) / 1000

def get_time_parts(time):
    millisecs = str(time).split(".")[1]
    if len(millisecs) != 3:
        millisecs = millisecs + ('0' * (3 - len(millisecs)))
    millisecs = int(millisecs)
    mins, secs = divmod(time, 60)
    hours, mins = divmod(mins, 60)

    return (hours, mins, secs, millisecs)

def seconds_to_srt_time(time):
    return '%02d:%02d:%02d,%03d' % get_time_parts(time)

def read_subtitles(content):
    subs = []
    
    content = re.sub('\n\n+', '\n\n', content)
    for sub in content.strip().split('\n\n'):
        sub_chunks = sub.split('\n')
        if (len(sub_chunks) >= 3):
            sub_timecode =  sub_chunks[1].split(' --> ')
            
            sub_start = srt_time_to_seconds(sub_timecode[0].strip())
            sub_end = srt_time_to_seconds(sub_timecode[1].strip())
            sub_content = " ".join(sub_chunks[2:]).replace("\t", " ")
            sub_content = re.sub(r"<[^>]+>", "", sub_content)
            sub_content = re.sub(r"  +", " ", sub_content)
            sub_content = sub_content.strip()

            if len(sub_content) > 0:
                subs.append((sub_start, sub_end, sub_content))
   
    return subs

def convert_into_sentences(en_subs, limit):
    subs = []

    for sub in en_subs:
        sub_start = sub[0]
        sub_end = sub[1]
        sub_content = sub[2]

        if len(subs) > 0: 
            prev_sub_start = subs[-1][0]
            prev_sub_end = subs[-1][1]
            prev_sub_content = subs[-1][2]

            if ((sub_start - prev_sub_end) <= 2 and (sub_end - prev_sub_start) < limit and sub_content[0] != '-' and
                prev_sub_content[-1] != '.' and 
                prev_sub_content[-1] != '?' and
                prev_sub_content[-1] != '!' and
                prev_sub_content[-1] != ']'):

                subs[-1] = (prev_sub_start, sub_end, prev_sub_content + " " + sub_content)
            else:
                subs.append((sub_start, sub_end, sub_content))
        else:
            subs.append((sub_start, sub_end, sub_content))

    return subs

def write_subtitles(filename, subs):
    f = open(filename, 'w')

    for idx in range(len(subs)):
        f.write("(%s, %s)" % (seconds_to_srt_time(subs[idx][0]), seconds_to_srt_time(subs[idx][1])))
        f.write("\t")
        f.write(subs[idx][2])
        f.write("\n")
    
    f.close()

def play_clips(clips):
    if len(clips) != 0:
        clip_filename, clip_start = clips[0]
        cmd = ["mpv", clip_filename, "--start=%s" % clip_start, "--input-ipc-server=\\\\.\pipe\mpv-pipe"]
        subprocess.Popen(cmd, shell=False)
        
        time.sleep(3) # wait 3 seconds for pipe has been created
        
        if not os.path.isfile("\\\\.\pipe\mpv-pipe"):
            print "Can't open '\\\\.\\pipe\\mpv-pipe'"
            return

        for clip_filename, clip_start in clips[1:]:
            clip_filename = clip_filename.replace("\\","/")
            cmd = ["echo", "loadfile", '"' + clip_filename + '"', "append start=%s" % clip_start]
            with open('\\\\.\pipe\mpv-pipe', "w") as mpv_pipe:
                subprocess.call(cmd, stdout=mpv_pipe)

def main(media_dir, search_phrase):
    cmd = ["grep", "-r", "-i", "--include", "\*.txt", "-E", search_phrase, media_dir]
        
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=-1)
    output, error = p.communicate()
    if p.returncode == 0:
        matches = output.splitlines()
        num_of_clips = len(matches)
        
        print "Number of clips:", num_of_clips
        
        clips = []
        for match in matches:
            filename, line = match.split(".txt:", 1)
            sub_timing, sub_content = line.split("\t", 1)            
            sub_start, sub_end = sub_timing.strip("()").split(", ")
            
            sub_start = srt_time_to_seconds(sub_start)

            for ext in movie_extensions:
                movie_filename = filename + "." + ext
                if os.path.isfile(movie_filename):    
                    clips.append((os.path.abspath(movie_filename), sub_start))
                    break

        play_clips(clips)

    elif p.returncode == 1:
        print "%r is not found in '%s'" % (search_phrase, media_dir)
    else:
        print '%s' % error

def need_update(media_dir):
    srt_counter = 0
    txt_counter = 0
    for root, dirs, files in os.walk(media_dir):
        for file in files:
            if file.endswith('.srt'):
                srt_counter += 1
            elif file.endswith('.txt'):
                txt_counter += 1

    if srt_counter != txt_counter:
        return True

    return False
        
def init(media_dir):
    for root, dirs, files in os.walk(media_dir):
        for file in files:
            file_ext = file.split('.')[-1]
            if file_ext == "srt":
                file_path = os.path.join(root, file)

                print file_path

                with open(file_path, 'r') as f_srt:
                    content = f_srt.read()
                    
                    subs = read_subtitles(content)
                    subs = convert_into_sentences(subs, 20)

                    write_subtitles(file_path[:-4] + ".txt", subs)

def usage():
    print "python videogrep.py <media_dir> <phrase>"
    print "python videogrep.py <media_dir> _init_"

if __name__ == '__main__':
    if len(sys.argv) == 3:
        media_dir = sys.argv[1]
        search_phrase = sys.argv[2]
        
        if search_phrase == "_init_":
            init(media_dir)
        else:
            if need_update(media_dir):
                print "Warning: number of '.srt' and '.txt' files doesn't match. Maybe you need to use 'videogrep <media_dir> _init_'."
            main(media_dir, search_phrase)
    else:
        usage()
