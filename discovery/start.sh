#!/bin/bash

script_abs_path="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )/$(basename "${BASH_SOURCE[0]}")"
work_dir=$(dirname "${script_abs_path}")
venv_dir="./.discovery-tool-venv"

cd "${work_dir}"

# if [ ! -d "${venv_dir}" ]; then
#     echo "Creating virtual environment..."
#     python3 -m venv "${venv_dir}"
#     source "${venv_dir}/bin/activate"
#     pip install -r "${work_dir}/requirements.txt"
#     playwright install 
#     echo "Virtual environment created."
# else
#     source "${venv_dir}/bin/activate"
# fi

python3 browser_runner.py &
streamlit run control_panel.py &