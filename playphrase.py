#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import random
import re
import shutil
import sys
import subprocess
import time
import locale

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

def read_subtitles(file_path):
    content = open(file_path, 'rb').read()

    if content[:3] == b'\xef\xbb\xbf': # with bom
        content = content[3:]

    ret_code, content = convert_to_unicode(content)
    if ret_code == False:
        sys.exit(1)

    subs = []
    content = content.replace('\r\n', '\n')
    content = content.replace('\r', '\n')
    content = re.sub('\n\n+', '\n\n', content)
    for sub in content.strip().split('\n\n'):
        sub_chunks = sub.split('\n')
        if (len(sub_chunks) >= 3):
            sub_timecode =  sub_chunks[1].split(' --> ')
            
            sub_start = srt_time_to_seconds(sub_timecode[0].strip())
            sub_end = srt_time_to_seconds(sub_timecode[1].strip())
            sub_content = "\n".join(sub_chunks[2:]).replace("\t", " ")
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
        sub_content = sub[2].replace('\n', ' ')

        if len(subs) > 0: 
            prev_sub_start = subs[-1][0]
            prev_sub_end = subs[-1][1]
            prev_sub_content = subs[-1][2]

            if ((sub_start - prev_sub_end) <= 2 and (sub_end - prev_sub_start) < limit and 
                sub_content[0] != '-' and
                sub_content[0] != '"' and
                sub_content[0] != '♪' and
                sub_content[0].isupper() != True and
                (prev_sub_content[-1] != '.' or (sub_content[0:3] == '...' or (prev_sub_content[-3:] == '...' and sub_content[0].islower()))) and 
                prev_sub_content[-1] != '?' and
                prev_sub_content[-1] != '!' and
                prev_sub_content[-1] != ']' and
                prev_sub_content[-1] != ')' and
                prev_sub_content[-1] != '♪' and
                prev_sub_content[-1] != '”' and
                prev_sub_content[-1] != '"'):

                subs[-1] = (prev_sub_start, sub_end, prev_sub_content + " " + sub_content)
            else:
                subs.append((sub_start, sub_end, sub_content))
        else:
            subs.append((sub_start, sub_end, sub_content))

    return subs

def filter_subtitles(subs, clip_start, clip_end):
    subs_filtered = []

    for idx in range(len(subs)):
        sub_start = subs[idx][0]
        sub_end = subs[idx][1]
        sub_content = subs[idx][2]
        
        if sub_end > clip_start and sub_start < clip_end:
            subs_filtered.append((sub_start - clip_start, sub_end - clip_start, sub_content))

        if sub_start > clip_end:
            break

    return subs_filtered

def write_subtitles(filename, subs):
    f = open(filename, 'w', encoding='utf-8')

    if filename.endswith('.srt'):
        for idx in range(len(subs)):
            f.write(str(idx+1) + "\n")
            f.write(seconds_to_srt_time(subs[idx][0]) + " --> " + seconds_to_srt_time(subs[idx][1]) + "\n")
            f.write(subs[idx][2] + "\n")
            f.write("\n")
    else:
        for idx in range(len(subs)):
            f.write("(%s, %s)" % (seconds_to_srt_time(subs[idx][0]), seconds_to_srt_time(subs[idx][1])))
            f.write("\t")
            f.write(subs[idx][2])
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

def update_progress(progress, num, max_num):
    width = 25
    n = int(progress / 100.0 * width)
    sys.stdout.write("\r %3d%% [%s%s%s] %d/%d" % (progress, "=" * n, ">", " " * (width - n), num, max_num))
    sys.stdout.flush()

def get_fragment_filename(phrase):
    s = phrase.strip().replace(' ', '_')
    s = s.replace('.*', '...')
    max_filename_length = 30
    if len(s) > max_filename_length:
        s = s[:max_filename_length] + "..."
    return re.sub(r'(?u)[^-\w\'\.]', '', s)

def subprocess_call(args):
    try:
        output = subprocess.check_output(args, stderr=subprocess.STDOUT, universal_newlines=True)
    except subprocess.CalledProcessError as e:
        print("\n\n", e.output)
        sys.exit(1)

def create_fragments(search_phrase, clips, export_mode, output_dir):
    idx = 1
    
    update_progress(0, 0, len(clips))
    for video_file, clip_start, clip_end in clips:
        fragment_filename = get_fragment_filename(search_phrase)

        if len(clips) > 1:
            fragment_filename += "_" + str(idx).zfill(3)

        fragment_filename = os.path.join(output_dir, fragment_filename)

        ss = clip_start
        to = clip_end
        t = to - ss

        t_fade = 0.2
        af = "afade=t=in:st=%s:d=%s,afade=t=out:st=%s:d=%s" % (0, t_fade, t - t_fade, t_fade)
        video_encoding_mode = "ultrafast"

        if export_mode["audio"]:
            cmd = ["ffmpeg", "-y", "-ss", str(ss), "-i", video_file, "-t", str(t), "-af", af, fragment_filename + ".mp3"]
            subprocess_call(cmd)

        if export_mode["video"]:
            cmd = ["ffmpeg", "-y", "-ss", str(ss), "-i", video_file, "-strict", "-2", "-t", str(t), "-map", "0", "-c:v", "libx264", "-preset", video_encoding_mode, "-c:a", "aac", "-ac", "2", "-af", af, fragment_filename + ".mp4"]
            subprocess_call(cmd)

        if export_mode["video-sub"]:
            srt_style = "FontName=Arial,FontSize=22"

            srt_filename = video_file[:-4] + ".srt"
            if srt_filename[1] == ":": # Windows
                srt_filename = srt_filename.replace("\\", "\\\\\\\\")
                srt_filename = srt_filename.replace(":", "\\\\:")
                srt_filename = srt_filename.replace(",", "\\\\\\,")
                srt_filename = srt_filename.replace("'", "\\\\\\'")

            vf = "subtitles=" + srt_filename + ":force_style='" + srt_style + "',setpts=PTS-STARTPTS"
            af = "afade=t=in:st=%s:d=%s,afade=t=out:st=%s:d=%s,asetpts=PTS-STARTPTS" % (ss, t_fade, to - t_fade, t_fade)

            cmd = ["ffmpeg", "-y", "-ss", str(ss), "-i", video_file, "-strict", "-2", "-t", str(t), "-map", "0", "-c:v", "libx264", "-preset", video_encoding_mode, "-c:a", "aac", "-ac", "2", "-vf", vf, "-af", af, "-copyts", fragment_filename + ".sub.mp4"]
            subprocess_call(cmd)

        if export_mode["subtitles"]:
            subtitles_filename = video_file.rsplit('.', 1)[0] + ".srt"
            subs = read_subtitles(subtitles_filename)
            subs = filter_subtitles(subs, clip_start, clip_end)
            write_subtitles(fragment_filename + ".srt", subs)

        update_progress(float(idx) / len(clips) * 100, idx, len(clips))
        
        idx += 1

def play_clips(clips, ending_mode, mpv_options):
    if len(clips) != 0:
        clip_filename, clip_start, clip_end = clips[0]
        
        pipe_name = "mpv-pipe"

        mpv_default_options = { "--idle":"once", "--no-terminal":True, "--force-window":"no", "--input-file":pipe_name }

        cmd = update_mpv_player_cmd(mpv_default_options, mpv_options)

        with open(pipe_name, 'w'): # create pipe
            pass

        p = subprocess.Popen(cmd) # start mpv player in idle mode
        
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
                        msg = " ".join(cmd) + "\n"
                        f_pipe.write(msg.encode('utf-8'))
                    else:
                        break
                except IOError as ex:
                    if ex.errno != 32:
                        print(ex)
                    if p != None:
                        p.kill()
                    return

def print_match(media_dir, filename, line, attrs={"prev_filename": None}):
    if filename.startswith(media_dir):
        filename = filename.replace(media_dir + os.sep, '', 1)

    if attrs["prev_filename"] != filename:
        print()
        print('-', filename)
        print()

    attrs["prev_filename"] = filename

    line = line.replace('\t', ' ')
    print(line)

def main(media_dir, search_phrase, phrase_mode, phrases_gap, padding, limit, output_dir, grep_file, ending_mode, randomize_mode, demo_mode, mpv_options, audio_mode, video_mode, video_with_sub_mode, subtitles_mode):
    search_phrase_in_grep = "(?s)\(\d\d:\d\d:\d\d,\d\d\d\, \d\d:\d\d:\d\d,\d\d\d\)\\t[^\\n]*" + search_phrase + "[^\\n]*"

    rg = shutil.which('rg')
    if rg:
        cmd = ["rg", "--no-heading", "--null-data", "-N", "-o", "-i", "-g", "*.txt", "-P", search_phrase_in_grep, media_dir]
    else:
        cmd = ["grep", "-r", "-z", "-o", "-i", "--include", "*.txt", "-P", search_phrase_in_grep, media_dir]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, bufsize=-1)
    output, error = p.communicate()

    media_dir = os.path.abspath(media_dir).replace('\\', '/').replace('/', os.sep)

    if p.returncode == 0:
        matches = output.rstrip("\x00").split("\x00")

        if grep_file != None:
            with open(grep_file, 'w') as f_results:
                f_results.write("\n".join(matches))

        clips = []
        for match in matches:
            filename, line = match.strip().split(".txt:", 1)

            filename = os.path.abspath(filename).replace('\\', '/').replace('/', os.sep)

            if demo_mode:
                print_match(media_dir, filename, line)

            lines = line.split('\n')

            def get_line_timings(line):
                sub_timing, sub_content = line.split("\t", 1)
                sub_start, sub_end = sub_timing.strip("()").split(", ")
                return (sub_start, sub_end)

            sub_start, sub_end = get_line_timings(lines[0])
            match_sub_start = srt_time_to_seconds(sub_start)
            
            sub_start, sub_end = get_line_timings(lines[-1])
            match_sub_end = srt_time_to_seconds(sub_end)
            
            phrase_start = match_sub_start
            phrase_end = match_sub_end

            if phrase_mode:
                with open(filename + ".txt") as f_txt:
                    txt_lines = f_txt.read().splitlines()

                    def find_line_number(lines, line):
                        for idx, lines in enumerate(lines):
                            if line in lines:
                                return idx + 1

                    line_number_start = find_line_number(txt_lines, lines[0])
                    line_number_end = find_line_number(txt_lines, lines[-1])

                    txt_line_start_idx = line_number_start - 1
                    txt_line_end_idx = line_number_end - 1

                    for txt_line in reversed(txt_lines[:line_number_start - 1]):
                        sub_timing, sub_content = txt_line.split("\t", 1)            
                        sub_start, sub_end = sub_timing.strip("()").split(", ")

                        sub_start = srt_time_to_seconds(sub_start)
                        sub_end = srt_time_to_seconds(sub_end)

                        if (phrase_start - sub_end) <= phrases_gap:
                            phrase_start = sub_start
                            txt_line_start_idx -= 1
                        else:
                            break

                    for txt_line in txt_lines[line_number_end:]:
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
                    clips.append((movie_filename, phrase_start - padding, phrase_end + padding))
                    break

        if demo_mode:
            print()

        if phrase_mode:
            print("Number of matches:", len(clips))
            clips = list(OrderedDict.fromkeys(clips)) # delete dublicates

        print("Number of clips:", len(clips))
        
        if randomize_mode:
            random.shuffle(clips)

        if audio_mode or video_mode or video_with_sub_mode or subtitles_mode:
            create_fragments(search_phrase, clips, {"audio": audio_mode, "video": video_mode, "video-sub": video_with_sub_mode, "subtitles": subtitles_mode}, output_dir)
        elif not demo_mode:
            play_clips(clips, ending_mode, mpv_options)

    elif p.returncode == 1:
        print("'%s' is not found in '%s'" % (search_phrase, media_dir))
    else:
        print('%s' % error)

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

    print("ERROR: Unknown encoding. Use srt file with 'utf-8' encoding.")
    return (False, file_content)

def init(media_dir, limit):
    for root, dirs, files in os.walk(media_dir):
        for file in files:
            file_ext = file.split('.')[-1]
            if file_ext == "srt":
                file_path = os.path.join(root, file)

                print(file_path)

                subs = read_subtitles(file_path)
                subs = convert_into_sentences(subs, limit)

                write_subtitles(file_path[:-4] + ".txt", subs)

def parse_args(argv):
    if len(argv) < 3:
        return False

    search_phrase = argv[-1]
    if len(search_phrase) == 0:
        print("Search phrase can't be empty")
        sys.exit(1)

    args = {"padding": 0, "limit": 60, "output_dir": ".", "grep_file": None, "phrase_mode": False, "phrases_gap":1.25, "search_phrase":search_phrase, "ending_mode":False, "randomize_mode":False, "demo_mode":False, "mpv_options":"", "audio_mode":False, "video_mode":False, "video_with_sub_mode":False, "subtitles_mode":False }
    
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
        elif argv[idx] == "--grep-output" or argv[idx] == "-g":
            if idx + 1 >= len(argv):
                return False
            args["grep_file"] = argv[idx + 1]
            idx += 1
        elif argv[idx] == "--output" or argv[idx] == "-o":
            if idx + 1 >= len(argv):
                return False
            args["output_dir"] = os.path.abspath(argv[idx + 1])
            if not os.path.exists(args["output_dir"]):
                os.makedirs(args["output_dir"])
            idx += 1
        elif argv[idx] == "--ending" or argv[idx] == "-e":
            args["ending_mode"] = True
        elif argv[idx] == "--randomize" or argv[idx] == "-r":
            args["randomize_mode"] = True
        elif argv[idx] == "--demo" or argv[idx] == "-d":
            args["demo_mode"] = True
        elif argv[idx] == "--audio" or argv[idx] == "-a":
            args["audio_mode"] = True
        elif argv[idx] == "--video" or argv[idx] == "-v":
            args["video_mode"] = True
        elif argv[idx] == "--video-sub" or argv[idx] == "-vs":
            args["video_with_sub_mode"] = True
        elif argv[idx] == "--subtitles" or argv[idx] == "-s":
            args["subtitles_mode"] = True
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

def validate_args(args):
    if not os.path.isdir(args["media_dir"]):
        print("ERROR: '{}' is not a folder".format(args["media_dir"]))
        return False
    if args["output_dir"]:
        if os.path.exists(args["output_dir"]) and not os.path.isdir(args["output_dir"]):
            print("ERROR: '{}' is not a folder".format(args["output_dir"]))
            return False
    if args["grep_file"]:
        if os.path.isdir(args["grep_file"]):
            print("ERROR: '{}' can't be a folder".format(args["grep_file"]))
            return False
    return True

def print_usage():
    print("Usage: playphrase -i <media_dir> <phrase>")
    print()
    print("Init: playphrase -i <media_dir> _init_")
    print()
    print("Additional options:")
    print("-p SECONDS, --padding", "     ", "padding in seconds to add to the start and the end of each clip (default=0.0 seconds)")
    print("-e SECONDS, --ending", "      ", "play only matching lines (or phrases)")
    print("-r, --randomize", "           ", "randomize the clips")
    print("-a, --audio", "               ", "create audio fragments")
    print("-v, --video", "               ", "create video fragments")
    print("-s, --subtitles", "           ", "create subtitles")
    print("-vs, --video-sub", "          ", "create video fragments with hardcoded subtitles")
    print("-o DIRNAME, --output", "      ", "the output folder for audio and video fragments (default=.)")
    print("-d, --demo", "                ", "only show grep results")
    print("-g FILENAME, --grep-output", "", "write the 'grep' output to the file")
    print("-ph GAP_BETWEEN_PHRASES, --phrases", "", "move the start time of the clip to the beginning of the current phrase (default=1.25 seconds)")
    print("-l SECONDS, --limit", "       ", "maximum phrase's duration (default=60 seconds)")
    print("-m OPTIONS, --mpv-options", " ", "mpv player options")

if __name__ == '__main__':
    os.environ["PATH"] += os.pathsep + "." + os.sep + "utils" + os.sep + "grep"
    os.environ["PATH"] += os.pathsep + "." + os.sep + "utils" + os.sep + "mpv"
    os.environ["PATH"] += os.pathsep + "." + os.sep + "utils" + os.sep + "ffmpeg"

    if "LC_ALL" not in os.environ:
        os.environ["LC_ALL"] = "en_US.utf8"

    args = parse_args(sys.argv[1:])

    if args == False:
        print_usage()
        sys.exit(1)

    if validate_args(args):
        if args["search_phrase"] == "_init_":
            init(args["media_dir"], args["limit"])
        else:
            if need_update(args["media_dir"]):
                print("WARNING: number of '.srt' and '.txt' files doesn't match. Maybe use 'playphrase -i <media_dir> _init_'.")
            
            main(args["media_dir"], args["search_phrase"], args["phrase_mode"], args["phrases_gap"], args["padding"], args["limit"], args["output_dir"], args["grep_file"], args["ending_mode"], args["randomize_mode"], args["demo_mode"], args["mpv_options"], args["audio_mode"], args["video_mode"], args["video_with_sub_mode"], args["subtitles_mode"])
