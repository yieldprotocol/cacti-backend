import zmq
import streamlit as st

# Invoke this with: streamlit run ./discovery/streamlit.py

# Set up the ZeroMQ context and socket
context = zmq.Context()
socket = context.socket(zmq.REQ)
socket.connect("tcp://localhost:5558")
# Get the current receive timeout
# timeout = socket.getsockopt(zmq.RCVTIMEO)
# print("Current timeout:", timeout, "milliseconds")

# Streamlit interface
st.title("Playwright Control Panel")

url_input = st.text_input("Enter the URL (include 'https://'):", "https://app.uniswap.org/")
send_button = st.button("Open URL")

# Send the URL and command via ZeroMQ
if send_button and url_input:
    message = {
        "command": "Open",
        "url": url_input
    }
    socket.send_json(message)
    st.success(f"URL sent: {url_input}")
    response = socket.recv_string()
    st.write(response)
else:
    st.info("Please enter a URL and press the Send URL button.")

st.markdown('### WalletConnect')
wc_input = st.text_input("Enter the walletconnect uri:", "wc:xyz")
wc_button = st.button("Start WC")

# Send the wc URI and command via ZeroMQ
if wc_button and wc_input:
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

# Get and set forkID session state variable
if 'forkID' not in st.session_state:
    st.session_state['forkID'] = '902db63e-9c5e-415b-b883-5701c77b3aa7'
message = {
        "command": "GetForkID"
}
socket.send_json(message)
# Set the receive timeout to 100 milliseconds (a tenth of a second)
socket.RCVTIMEO = 100
response = None
try:
    # Receive data from the server
    response = socket.recv_json()
    print("Received data:", response)
except zmq.Again as e:
    print("Timeout: No response received within 0.1 seconds")
if response:
    st.session_state["forkID"] = response["id"] 
socket.RCVTIMEO = - 1

# Define input box for forkID
fork_id = st.text_input("Enter fork ID", value=st.session_state['forkID'])
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
        message = {
                "command": "NewFork"
        }
        socket.send_json(message)
        response = socket.recv_json()
        st.session_state["forkID"] = response["id"] 
        # Populate input box with new unique ID
        # st.write(f"New Fork: {response['id']}")
        st.experimental_rerun()
        


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
        st.write(response)


with col2:
    if st.button("End Forward"):
        # Send a message to the server to exit
        message = {
            "command": "endForward"
        }
        socket.send_json(message)
        response = socket.recv_string()
        st.write(response)

st.markdown('### Close Playwright App')
if st.button("Close"):
    # Send a message to the server to exit
    message = {
        "command": "Exit"
    }
    socket.send_json(message)
    response = socket.recv_string()
    st.write(response)
    # Clean up ZeroMQ
    socket.close()
    context.term()