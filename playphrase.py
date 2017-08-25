#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import random
import re
import sys
import subprocess
import time

from collections import OrderedDict

movie_extensions = ['mp4', 'avi', 'mkv', 'mp3']
srt_encodings = ["utf-8", "cp1251"]

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

            if ((sub_start - prev_sub_end) <= 2 and (sub_end - prev_sub_start) < limit and 
                sub_content[0] != '-' and
                sub_content[0] != '"' and
                sub_content[0] != u'♪' and
                (prev_sub_content[-1] != '.' or (sub_content[0:3] == '...' or (prev_sub_content[-3:] == '...' and sub_content[0].islower()))) and 
                prev_sub_content[-1] != '?' and
                prev_sub_content[-1] != '!' and
                prev_sub_content[-1] != ']' and
                prev_sub_content[-1] != ')' and
                prev_sub_content[-1] != u'♪' and
                prev_sub_content[-1] != u'”' and
                prev_sub_content[-1] != '"'):

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
        f.write(subs[idx][2].encode('utf-8'))
        f.write("\n")
    
    f.close()

def update_mpv_player_cmd(cmd_options, mpv_options):
    for opt in mpv_options.split():
        if "=" in opt:
            key, value = opt.split("=", 1)
            cmd_options[key] = value
        else:
            cmd_options[opt] = True

    cmd = ["mpv"]
    for opt in cmd_options:
        if cmd_options[opt] == True:
            cmd.append(opt)
        else:
            cmd.append(opt + "=" + cmd_options[opt])

    return cmd

def play_clips(clips, ending_mode, mpv_options):
    if len(clips) != 0:
        clip_filename, clip_start, clip_end = clips[0]
        
        pipe_name = "mpv-pipe"

        mpv_default_options = { "--idle":"once", "--no-terminal":True, "--force-window":"no", "--input-file":pipe_name }

        cmd = update_mpv_player_cmd(mpv_default_options, mpv_options)

        with open(pipe_name, 'w'): # create pipe
            pass

        p = subprocess.Popen(cmd, shell=False) # start mpv player in idle mode
        
        with open(pipe_name, "wb", 0) as f_pipe:
            for clip_filename, clip_start, clip_end in clips:
                clip_filename = clip_filename.replace("\\","/")
                
                cmd = ["loadfile", '"' + clip_filename + '"']
                if ending_mode:
                    cmd.append("append-play start=%s,end=%s" % (clip_start, clip_end))
                else:
                    cmd.append("append-play start=%s" % clip_start)
                
                try:
                    if p.poll() == None:
                        f_pipe.write(" ".join(cmd) + "\n")
                    else:
                        break
                except IOError as ex:
                    if ex.errno != 32:
                        print ex
                    if p != None:
                        p.kill()
                    return

def main(media_dir, search_phrase, phrase_mode, phrases_gap, padding, limit, output_file, ending_mode, randomize_mode, demo_mode, mpv_options):
    cmd = " ".join(["grep", "-r", "-n", "-i", "--include", "\*.txt", "-P", '"' + search_phrase + '"', '"' + media_dir + '"'])
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True, bufsize=-1)
    output, error = p.communicate()

    if p.returncode == 0:
        if output_file != None:
            with open(output_file, 'w') as f_results:
                f_results.write(output)

        matches = output.splitlines()
        
        clips = []
        for match in matches:
            filename, line = match.split(".txt:", 1)
            line_number, line = line.split(":", 1)
            line_number = int(line_number)
            
            sub_timing, sub_content = line.split("\t", 1)            
            sub_start, sub_end = sub_timing.strip("()").split(", ")
            
            match_sub_start = srt_time_to_seconds(sub_start)
            match_sub_end = srt_time_to_seconds(sub_end)

            phrase_start = match_sub_start
            phrase_end = match_sub_end

            if phrase_mode:
                with open(filename + ".txt") as f_txt:
                    txt_lines = f_txt.read().splitlines()

                    txt_line_start_idx = line_number - 1
                    txt_line_end_idx = line_number - 1

                    for txt_line in reversed(txt_lines[:line_number - 1]):
                        sub_timing, sub_content = txt_line.split("\t", 1)            
                        sub_start, sub_end = sub_timing.strip("()").split(", ")

                        sub_start = srt_time_to_seconds(sub_start)
                        sub_end = srt_time_to_seconds(sub_end)

                        if (phrase_start - sub_end) <= phrases_gap:
                            phrase_start = sub_start
                            txt_line_start_idx -= 1
                        else:
                            break

                    for txt_line in txt_lines[line_number:]:
                        sub_timing, sub_content = txt_line.split("\t", 1)            
                        sub_start, sub_end = sub_timing.strip("()").split(", ")

                        sub_start = srt_time_to_seconds(sub_start)
                        sub_end = srt_time_to_seconds(sub_end)

                        if (sub_start - phrase_end) <= phrases_gap:
                            phrase_end = sub_end
                            txt_line_end_idx += 1
                        else:
                            break

                    if (phrase_end - phrase_start) > limit:
                        phrases_lines = txt_lines[txt_line_start_idx: txt_line_end_idx + 1]

                        sub_chunks_num = int((phrase_end - phrase_start) / limit) + 1
                        
                        sub_splitted = [[] for i in range(sub_chunks_num)]
                        
                        sub_chunks_limit = (phrase_end - phrase_start + 1) / sub_chunks_num

                        for phrase_line in phrases_lines:
                            phrase_timing, phrase_line_content = phrase_line.split("\t", 1)            
                            phrase_line_start, phrase_line_end = phrase_timing.strip("()").split(", ")

                            phrase_line_start = srt_time_to_seconds(phrase_line_start)
                            phrase_line_end = srt_time_to_seconds(phrase_line_end)

                            pos = int((phrase_line_end - phrase_start) / sub_chunks_limit)

                            sub_splitted[pos].append((phrase_line_start, phrase_line_end))

                        match_sub_pos = int((match_sub_end - phrase_start) / sub_chunks_limit)

                        phrase_start = sub_splitted[match_sub_pos][0][0]
                        phrase_end = sub_splitted[match_sub_pos][-1][1]

            for ext in movie_extensions:
                movie_filename = filename + "." + ext
                if os.path.isfile(movie_filename):
                    clips.append((os.path.abspath(movie_filename), phrase_start - padding, phrase_end + padding))
                    break

        if phrase_mode:
            print "Number of matches:", len(clips)
            clips = list(OrderedDict.fromkeys(clips)) # delete dublicates
        
        print "Number of clips:", len(clips)
        
        if randomize_mode:
            random.shuffle(clips)

        if not demo_mode:
            play_clips(clips, ending_mode, mpv_options)

    elif p.returncode == 1:
        print "'%s' is not found in '%s'" % (search_phrase, media_dir)
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

def convert_to_unicode(file_content):
    for enc in srt_encodings:
        try:
            content = file_content.decode(enc)
            return (True, content)
        except UnicodeDecodeError:
            pass

    print "ERROR: Unknown encoding. Use srt file with 'utf-8' encoding."
    return (False, file_content)

def init(media_dir, limit):
    for root, dirs, files in os.walk(media_dir):
        for file in files:
            file_ext = file.split('.')[-1]
            if file_ext == "srt":
                file_path = os.path.join(root, file)

                print file_path

                with open(file_path, 'rU') as f_srt:
                    content = f_srt.read()
                    if content[:3]=='\xef\xbb\xbf': # with bom
                        content = content[3:]
                    ret_code, content = convert_to_unicode(content)
                    if ret_code == False:
                        sys.exit(1)

                subs = read_subtitles(content)
                subs = convert_into_sentences(subs, limit)

                write_subtitles(file_path[:-4] + ".txt", subs)

def parse_args(argv):
    if len(argv) < 3:
        return False

    search_phrase = argv[-1]
    if len(search_phrase) == 0:
        print "Search phrase can't be empty"
        sys.exit()

    args = {"padding": 0, "limit": 15, "output_file": None, "phrase_mode": False, "phrases_gap":1.75, "search_phrase":search_phrase, "ending_mode":False, "randomize_mode":False, "demo_mode":False, "mpv_options":""}
    
    argv = argv[:-1]
    idx = 0
    while idx < len(argv):
        if argv[idx] == "--input" or argv[idx] == "-i":
            if idx + 1 >= len(argv):
                return False
            args["media_dir"] = argv[idx + 1]
            idx += 1
        elif argv[idx] == "--padding" or argv[idx] == "-p":
            if idx + 1 >= len(argv):
                return False
            args["padding"] = float(argv[idx + 1])
            idx += 1
        elif argv[idx] == "--limit" or argv[idx] == "-l":
            if idx + 1 >= len(argv):
                return False
            args["limit"] = int(argv[idx + 1])
            idx += 1
        elif argv[idx] == "--output" or argv[idx] == "-o":
            if idx + 1 >= len(argv):
                return False
            args["output_file"] = argv[idx + 1]
            idx += 1
        elif argv[idx] == "--ending" or argv[idx] == "-e":
            args["ending_mode"] = True
        elif argv[idx] == "--randomize" or argv[idx] == "-r":
            args["randomize_mode"] = True
        elif argv[idx] == "--demo" or argv[idx] == "-d":
            args["demo_mode"] = True
        elif argv[idx] == "--phrases" or argv[idx] == "-ph":
            args["phrase_mode"] = True
            if idx + 1 < len(argv):
                try:
                    phrases_gap = float(argv[idx + 1])
                    args["phrases_gap"] = phrases_gap
                    idx += 1
                except ValueError:
                    pass
        elif argv[idx] == "--mpv-options" or argv[idx] == "-m":
            if idx + 1 >= len(argv):
                return False
            args["mpv_options"] = argv[idx + 1]
            idx += 1
        else:
            return False

        idx += 1

    if "media_dir" not in args:
        return False
    
    return args

def usage():
    print "python videogrep.py -i <media_dir> <phrase>"
    print "python videogrep.py -i <media_dir> _init_"
    print ""
    print "Additional options:"
    print "-ph, --phrases GAP_BETWEEN_PHRASES", "\t", "move start time of the clip to the beginning of the current phrase. Value is optional (default=1.75 seconds)"
    print "-l, --limit", "\t", "maximum duration of the phrase (default=30 seconds)"
    print "-p, --padding", "\t", "padding in seconds to add to the start and end of each clip (default=0.0 seconds)"
    print "-e, --ending", "\t", "play only matching lines (or phrases)"
    print "-r, --randomize", "\t", "randomize the clips"
    print "-o, --output", "\t", "name of the file in which output of \'grep\' command will be written"
    print "-d, --demo", "\t", "only show grep results"
    print "-m, --mpv-options OPTIONS", "\t", "mpv player options"

if __name__ == '__main__':
    os.environ["PATH"] += os.pathsep + "." + os.sep + "utils" + os.sep + "grep"
    os.environ["PATH"] += os.pathsep + "." + os.sep + "utils" + os.sep + "mpv"

    args = parse_args(sys.argv[1:])
    if args != False:
        if args["search_phrase"] == "_init_":
            init(args["media_dir"], args["limit"])
        else:
            if need_update(args["media_dir"]):
                print "WARNING: number of '.srt' and '.txt' files doesn't match. Maybe you need to use 'videogrep <media_dir> _init_'."
            
            main(args["media_dir"], args["search_phrase"], args["phrase_mode"], args["phrases_gap"], args["padding"], args["limit"], args["output_file"], args["ending_mode"], args["randomize_mode"], args["demo_mode"], args["mpv_options"])
    else:
        usage()
