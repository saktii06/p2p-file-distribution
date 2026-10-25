import os
import sys
import socket
import tempfile

project_folder = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

sys.path.insert(0, project_folder)

from peer.peer_server import PeerServer
from peer.peer_protocol import (
    create_handshake,
    create_request,
    receive_message,
    send_message,
    decode_piece
)


def main():
    print("=" * 45)
    print("PEER SERVER TESTS")
    print("=" * 45)

    # Create a temporary file to share.
    with tempfile.NamedTemporaryFile(
        mode="wb",
        delete=False
    ) as file:
        file.write(b"Hello from the P2P peer server!")
        file_path = file.name

    server = PeerServer(
        peer_id="peer_A",
        file_id="sample-file",
        file_path=file_path,
        port=0
    )

    client = None

    try:
        print("\n1. Starting peer server...")
        server.start()

        print("PASS: Peer server started.")

        print("\n2. Connecting to peer server...")

        client = socket.create_connection(
            ("127.0.0.1", server.port),
            timeout=5
        )

        client.settimeout(5)

        send_message(
            client,
            create_handshake("peer_B", "sample-file")
        )

        response = receive_message(client)

        assert response["type"] == "HANDSHAKE"
        assert response["peer_id"] == "peer_A"

        print("PASS: Handshake completed.")

        bitfield = receive_message(client)

        assert bitfield["type"] == "BITFIELD"
        assert bitfield["pieces"] == [0]

        print("PASS: Bitfield received correctly.")

        print("\n3. Requesting a file piece...")

        send_message(client, create_request(0))

        piece_message = receive_message(client)

        assert piece_message["type"] == "PIECE"
        assert piece_message["piece_index"] == 0

        received_data = decode_piece(piece_message)

        assert received_data == b"Hello from the P2P peer server!"

        print("PASS: File piece received correctly.")
        print("Received data:", received_data.decode("utf-8"))

        print("\n" + "=" * 45)
        print("ALL PEER SERVER TESTS PASSED!")
        print("=" * 45)

    finally:
        if client:
            client.close()

        server.stop()

        if os.path.exists(file_path):
            os.remove(file_path)


if __name__ == "__main__":
    main()