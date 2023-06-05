#!/bin/bash

xvfb_cmd=xvfb-run
start_cmd="uvicorn main:app --host 0.0.0.0 --port 9999"

if [[ $(type -P "$xvfb_cmd") ]]
then
    $xvfb_cmd $start_cmd
else
    $start_cmd
fi
