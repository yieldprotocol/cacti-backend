import zmq
import streamlit as st

# Invoke this with: streamlit run ./discovery/streamlit.py

# Set up the ZeroMQ context and socket
context = zmq.Context()
socket = context.socket(zmq.REQ)
socket.connect("tcp://localhost:5558")

# Streamlit interface
st.title("Playwright Control Panel")

url_input = st.text_input("Enter the URL (include 'https://'):", "https://www.google.com/")
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
else:
    st.info("Please enter a WalletConnect URI and presss Start WC button.")

if st.button("Exit"):
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