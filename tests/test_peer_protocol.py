import os
import sys
import socket

project_folder = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

sys.path.insert(0, project_folder)

from peer.peer_protocol import (
    create_handshake,
    create_bitfield,
    create_have,
    create_request,
    create_piece,
    decode_piece,
    create_cancel,
    send_message,
    receive_message,
    validate_message
)


def test_message_types():
    """Test the creation and validation of all six message types."""

    print("\n1. Testing message creation...")

    handshake = create_handshake("peer_A", "sample-file")
    bitfield = create_bitfield([0, 2, 4])
    have = create_have(3)
    request = create_request(2)
    piece = create_piece(2, b"Hello P2P")
    cancel = create_cancel(2)

    messages = [
        handshake,
        bitfield,
        have,
        request,
        piece,
        cancel
    ]

    for message in messages:
        assert validate_message(message)

    assert handshake["type"] == "HANDSHAKE"
    assert bitfield["pieces"] == [0, 2, 4]
    assert have["piece_index"] == 3
    assert request["piece_index"] == 2
    assert decode_piece(piece) == b"Hello P2P"
    assert cancel["piece_index"] == 2

    print("PASS: All six message types were created and validated.")


def test_socket_communication():
    """Test sending and receiving messages through a socket."""

    print("\n2. Testing socket communication...")

    sender, receiver = socket.socketpair()

    try:
        original_message = create_handshake(
            "peer_A",
            "sample-file"
        )

        send_message(sender, original_message)

        received_message = receive_message(receiver)

        assert received_message == original_message

        print("PASS: Handshake message sent and received correctly.")

        # Test a PIECE message containing binary data
        original_data = b"Binary data: \x00\x01\x02\xff"

        piece_message = create_piece(1, original_data)

        send_message(sender, piece_message)

        received_piece = receive_message(receiver)

        assert received_piece["piece_index"] == 1
        assert decode_piece(received_piece) == original_data

        print("PASS: Binary piece data transferred correctly.")

    finally:
        sender.close()
        receiver.close()


def test_invalid_message():
    """Test that an unsupported message type is rejected."""

    print("\n3. Testing invalid message rejection...")

    invalid_message = {
        "type": "UNKNOWN"
    }

    try:
        validate_message(invalid_message)
    except ValueError:
        print("PASS: Unknown message type was rejected.")
    else:
        raise AssertionError("Unknown message type was accepted.")


def main():
    print("=" * 45)
    print("PEER PROTOCOL TESTS")
    print("=" * 45)

    test_message_types()
    test_socket_communication()
    test_invalid_message()

    print("\n" + "=" * 45)
    print("ALL PEER PROTOCOL TESTS PASSED!")
    print("=" * 45)


if __name__ == "__main__":
    main()