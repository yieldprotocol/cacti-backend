#!/bin/bash

on_ctrl_c() {
    # Kill any pending zmq processes
    lsof -i :5558 | awk 'NR>1 {print $2}' | xargs kill -9
}

python3 playwright_browser.py &
pid1=$! 

streamlit run streamlit_control_panel.py &
pid2=$!

trap on_ctrl_c SIGINT

wait $pid1
wait $pid2


