import signal
import subprocess
import os
import zmq
import streamlit as st


# Invoke this with: streamlit run ./discovery/streamlit.py

# New fork ID: 902db63e-9c5e-415b-b883-5701c77b3aa7
# Forwarding Started

# Set up the ZeroMQ context and socket
context = zmq.Context()
socket = context.socket(zmq.REQ)
socket.connect("tcp://localhost:5558")


def kill_streamlit_server():
    process_name = "streamlit_control_panel"

    output = subprocess.check_output(['ps', 'aux']).decode('utf-8')

    # Split the output into lines and iterate through them
    for line in output.strip().split('\n'):
        # Check if the partial name is in the process name
        if process_name.lower() in line.lower():
            # Extract the process ID (PID) from the line
            pid = int(line.split()[1])

            # Kill the process
            print(f'Killing process with PID: {pid}')
            os.kill(pid, signal.SIGKILL)

if 'fork_forwarding_text' not in st.session_state:
    st.session_state.fork_forwarding_text = ""


# Init code to run when the page loads
def init_page():
    # Set Fork ID
    socket.send_json({ "command": "ForkID", "id": st.session_state.fork_id })
    st.session_state.fork_forwarding_text = f"Fork ID: {st.session_state.fork_id}, forwarding already started by default on page load"
    response = socket.recv_string()
    print("Received Fork ID data:", response)

    # On page load, by default, forward traffic to Tenderly
    socket.send_json({ "command": "Forward" })
    response = socket.recv_string()
    print("Received Fork Forwarding data:", response)

# Streamlit interface
st.title("Playwright Control Panel")

url_input = st.text_input("Enter the URL (include 'https://'):", value="https://app.aave.com")
send_url_button = st.button("Open URL", disabled=not url_input)
# Send the URL and command via ZeroMQ
if send_url_button:
    message = {
        "command": "Open",
        "url": url_input
    }
    socket.send_json(message)
    st.success(f"URL sent: {url_input}")
    response = socket.recv_string()
    st.write(response)

    init_page()
else:
    st.info("Please enter a URL and press the Send URL button.")

st.markdown('### WalletConnect')
wc_input = st.text_input("Enter the walletconnect uri:", placeholder="wc:xyz")
wc_button = st.button("Start WC", disabled=not wc_input)
# Send the wc URI and command via ZeroMQ
if wc_button:
    message = {
        "command": "WC",
        "wc": wc_input
    }
    socket.send_json(message)
    st.success(f"wc sent: {url_input}")
    response = socket.recv_string()
    st.write(response)
# else:
#    st.info("Please enter a WalletConnect URI and presss Start WC button.")

# Define Streamlit app header
st.markdown("### Fork Manager")
# Define input box for forkID
fork_id = st.text_input("Enter fork ID", key="fork_id", value="08f78838-4799-47a8-88fb-1f169fa99f57")
col1, col2 = st.columns(2)
# Define button to update fork
with col1:
    if st.button("Update Fork"):
        # Send unique ID to server via ZMQ
        message = {
                "command": "ForkID",
                "id": fork_id
        }
        socket.send_json(message)
        response = socket.recv_string()
        st.write(f"Response received: {response}")

# Define button to create new fork
with col2:
    if st.button("New Fork"):
        # Send message to server to create new fork and receive unique ID
        st.write(f"Not yet implemented")
        '''
        message = {
                "command": "NewFork"
        }
        socket.send_json(message)
        response = socket.recv_json()
        st.session_state["forkID"] = response["id"] 
        # Populate input box with new unique ID
        # st.write(f"New Fork: {response['id']}")
        st.experimental_rerun()
        '''

st.markdown('### Forwarding Traffic to Tenderly')
col1, col2 = st.columns(2)
with col1:
    if st.button("Forward"):
        # Send a message to the server to exit
        message = {
            "command": "Forward"
        }
        socket.send_json(message)
        response = socket.recv_string()
        st.session_state.fork_forwarding_text = f"Fork ID: {st.session_state.fork_id}, {response}"

with col2:
    if st.button("End Forward"):
        # Send a message to the server to exit
        message = {
            "command": "endForward"
        }
        socket.send_json(message)
        response = socket.recv_string()
        st.write(response)

st.success(st.session_state.fork_forwarding_text)

st.markdown('### Shutdown Control Panel and Playwright Browser')
if st.button("Shutdown"):
    # Send a message to the server to exit
    message = {
        "command": "Exit"
    }
    socket.send_json(message)
    response = socket.recv_string()
    st.warning(response)
    # Clean up ZeroMQ
    socket.close()
    context.term()
    st.warning("Control Panel shutdown, close tab, re-run start script to restart.")
    # No clean way to shutdown Streamlit server so have to resort to killng the process
    kill_streamlit_server()
