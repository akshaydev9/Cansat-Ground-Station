import csv
import os
import threading
from pathlib import Path

import serial
from flask import Flask, request, send_file
from flask_socketio import SocketIO


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_BAUD_RATE = 115200

app = Flask(__name__)
socketio = SocketIO(app, async_mode="threading")

receiver_lock = threading.Lock()
receiver_thread = None
receiver_stop_event = None


@app.get("/")
def dashboard():
    return send_file(BASE_DIR / "index.html")


def emit_status(client_id, state, message, port=None, baud_rate=None):
    status = {"state": state, "message": message}
    if port is not None:
        status["port"] = port
    if baud_rate is not None:
        status["baud_rate"] = baud_rate
    socketio.emit("receiver_status", status, to=client_id)


def read_receiver(port, baud_rate, client_id, stop_event):
    global receiver_thread, receiver_stop_event
    try:
        with serial.Serial(port, baud_rate, timeout=1) as device:
            emit_status(
                client_id,
                "connected",
                f"Receiver connected on {port} at {baud_rate} baud.",
                port,
                baud_rate,
            )

            while not stop_event.is_set():
                packet_bytes = device.readline()
                if not packet_bytes:
                    continue

                raw_packet = packet_bytes.decode("utf-8", errors="replace").strip()
                if not raw_packet:
                    continue

                try:
                    fields = next(csv.reader([raw_packet]))
                except csv.Error as error:
                    socketio.emit(
                        "packet_warning",
                        {"message": f"Could not parse CSV packet: {error}"},
                        to=client_id,
                    )
                    continue

                if len(fields) < 15:
                    socketio.emit(
                        "packet_warning",
                        {
                            "message": (
                                f"Packet has {len(fields)} fields; the dashboard needs "
                                "at least 15. Check the packet format."
                            )
                        },
                        to=client_id,
                    )
                    continue

                socketio.emit("telemetry_packet", {"raw": raw_packet}, to=client_id)
    except (serial.SerialException, OSError, ValueError) as error:
        emit_status(
            client_id,
            "error",
            f"Could not open/read {port}: {error}. Check the COM port, baud rate, and that no other app is using it.",
        )
    finally:
        with receiver_lock:
            if receiver_stop_event is stop_event:
                receiver_thread = None
                receiver_stop_event = None
        if stop_event.is_set():
            emit_status(client_id, "disconnected", "Receiver disconnected.")


@socketio.on("connect_receiver")
def connect_receiver(request_data):
    global receiver_thread, receiver_stop_event
    request_data = request_data or {}
    port = str(request_data.get("port", "")).strip()

    try:
        baud_rate = int(request_data.get("baud_rate", DEFAULT_BAUD_RATE))
        if baud_rate <= 0:
            raise ValueError("Baud rate must be a positive number.")
    except (TypeError, ValueError) as error:
        emit_status(request.sid, "error", f"Invalid baud rate: {error}")
        return

    if not port:
        emit_status(request.sid, "error", "Enter the ground receiver's COM port.")
        return

    with receiver_lock:
        if receiver_thread is not None and receiver_thread.is_alive():
            emit_status(
                request.sid,
                "error",
                "A receiver connection is already active. Disconnect it before connecting again.",
            )
            return

        receiver_stop_event = threading.Event()
        receiver_thread = threading.Thread(
            target=read_receiver,
            args=(port, baud_rate, request.sid, receiver_stop_event),
            daemon=True,
        )
        receiver_thread.start()


@socketio.on("disconnect_receiver")
def disconnect_receiver():
    with receiver_lock:
        if receiver_stop_event is not None:
            receiver_stop_event.set()
        else:
            emit_status(request.sid, "disconnected", "No receiver connection is active.")


if __name__ == "__main__":
    configured_port = os.environ.get("SERIAL_PORT")
    if configured_port:
        print(
            f"Default receiver port: {configured_port} "
            f"(the dashboard COM field can override it)."
        )
    print("Open http://127.0.0.1:5000 to use the ground-station dashboard.")
    socketio.run(
        app,
        host="127.0.0.1",
        port=5000,
        debug=False,
        use_reloader=False,
    )
