@echo off
setlocal EnableDelayedExpansion

set media_dir="J:\English AudioBooks"

for /L %%n in (1,0,1) do (
    set /p phrase="Phrase: "

    if /I "!phrase!"=="q" call :stop
    if /I "!phrase!"=="x" call :stop
    if /I "!phrase!"=="quit" call :stop
    if /I "!phrase!"=="exit" call :stop

    rem Disable album cover art and create a window even if there is no album cover art.
    rem python playphrase.py --mpv-options "--video=no --force-window=yes --osc=no --title=${filename}" --input "%media_dir%" "!phrase!"

    python playphrase.py --mpv-options "--sub-font-size=37 --sub-back-color=0.05/0.9 --sub-scale-by-window=no --sub-scale-with-window=no --autofit=620 --osc=no --title=${filename}" --input "%media_dir%" "!phrase!"
)

:stop
call :__stop 2>nul

:__stop
() creates a syntax error, quits the batch
