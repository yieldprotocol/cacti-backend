#!/bin/bash

export LANGCHAIN_HANDLER=langchain
xvfb_cmd=xvfb-run

[[ $(type -P "$xvfb_cmd") ]] && $xvfb_cmd python3 server.py || python3 server.py
