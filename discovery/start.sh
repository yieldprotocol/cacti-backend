#!/bin/bash

on_ctrl_c() {
    # Kill any pending zmq processes
    kill $(lsof -t -i :5558)  
}

python3 browser_runner.py &
pid1=$! 

streamlit run control_panel.py &
pid2=$!

trap on_ctrl_c SIGINT

wait $pid1
wait $pid2


