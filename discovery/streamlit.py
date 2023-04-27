import zmq
import streamlit as st

# Set up the ZeroMQ context and socket
context = zmq.Context()
socket = context.socket(zmq.REQ)
socket.connect("tcp://localhost:5555")

# Streamlit interface
st.title("Playwright Control Panel")

if st.button("Open Google"):
    # Send a message to the server to open Google
    socket.send_string("Open Google")
    response = socket.recv_string()
    st.write(response)

if st.button("Exit"):
    # Send a message to the server to exit
    socket.send_string("Exit")
    response = socket.recv_string()
    st.write(response)
    # Clean up ZeroMQ
    socket.close()
    context.term()