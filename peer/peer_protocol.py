import base64
import json
import socket
import struct

# Maximum size of one encoded protocol message: 16 MB
MAX_MESSAGE_SIZE = 16 * 1024 * 1024

# Message types supported by our protocol
MESSAGE_TYPES = {
    "HANDSHAKE",
    "BITFIELD",
    "HAVE",
    "REQUEST",
    "PIECE",
    "CANCEL"
}


def create_handshake(peer_id, file_id):
    """Create a handshake message."""

    return {
        "type": "HANDSHAKE",
        "peer_id": peer_id,
        "file_id": file_id
    }


def create_bitfield(piece_indexes):
    """Create a message describing the pieces a peer possesses."""

    return {
        "type": "BITFIELD",
        "pieces": piece_indexes
    }


def create_have(piece_index):
    """Announce that a peer has obtained a piece."""

    return {
        "type": "HAVE",
        "piece_index": piece_index
    }


def create_request(piece_index):
    """Request a particular piece from another peer."""

    return {
        "type": "REQUEST",
        "piece_index": piece_index
    }


def create_piece(piece_index, piece_data):
    """Create a message containing piece data."""

    encoded_data = base64.b64encode(piece_data).decode("ascii")

    return {
        "type": "PIECE",
        "piece_index": piece_index,
        "data": encoded_data
    }


def decode_piece(message):
    """Decode the binary data inside a PIECE message."""

    if message.get("type") != "PIECE":
        raise ValueError("Message is not a PIECE message.")

    try:
        return base64.b64decode(message["data"], validate=True)
    except (KeyError, ValueError) as error:
        raise ValueError("Invalid piece data.") from error


def create_cancel(piece_index):
    """Cancel a request for a particular piece."""

    return {
        "type": "CANCEL",
        "piece_index": piece_index
    }


def validate_message(message):
    """Check the basic structure of a protocol message."""

    if not isinstance(message, dict):
        raise ValueError("Message must be a dictionary.")

    message_type = message.get("type")

    if message_type not in MESSAGE_TYPES:
        raise ValueError("Unknown message type.")

    # Check the required fields for each message
    if message_type == "HANDSHAKE":
        if not message.get("peer_id") or not message.get("file_id"):
            raise ValueError("Handshake requires peer_id and file_id.")

    elif message_type == "BITFIELD":
        pieces = message.get("pieces")

        if not isinstance(pieces, list):
            raise ValueError("Bitfield pieces must be a list.")

        if any(
            not isinstance(index, int)
            or isinstance(index, bool)
            or index < 0
            for index in pieces
        ):
            raise ValueError("Bitfield contains an invalid piece index.")

    elif message_type in {"HAVE", "REQUEST", "CANCEL"}:
        index = message.get("piece_index")

        if (
            not isinstance(index, int)
            or isinstance(index, bool)
            or index < 0
        ):
            raise ValueError("Invalid piece index.")

    elif message_type == "PIECE":
        index = message.get("piece_index")

        if (
            not isinstance(index, int)
            or isinstance(index, bool)
            or index < 0
        ):
            raise ValueError("Invalid piece index.")

        # Check that the piece data can be decoded
        decode_piece(message)

    return True


def receive_exactly(connection, number_of_bytes):
    """Receive exactly the requested number of bytes."""

    data = bytearray()

    while len(data) < number_of_bytes:
        chunk = connection.recv(number_of_bytes - len(data))

        if not chunk:
            raise ConnectionError("Connection closed unexpectedly.")

        data.extend(chunk)

    return bytes(data)


def send_message(connection, message):
    """Send one length-prefixed JSON message over a socket."""

    validate_message(message)

    message_bytes = json.dumps(message).encode("utf-8")

    if len(message_bytes) > MAX_MESSAGE_SIZE:
        raise ValueError("Message exceeds the maximum allowed size.")

    # Encode the message length as a 4-byte unsigned integer
    header = struct.pack("!I", len(message_bytes))

    connection.sendall(header + message_bytes)


def receive_message(connection):
    """Receive and decode one length-prefixed JSON message."""

    # First, read the 4-byte length header
    header = receive_exactly(connection, 4)

    message_length = struct.unpack("!I", header)[0]

    if message_length == 0 or message_length > MAX_MESSAGE_SIZE:
        raise ValueError("Invalid message length.")

    # Then, read the complete message
    message_bytes = receive_exactly(connection, message_length)

    try:
        message = json.loads(message_bytes.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ValueError("Invalid JSON message.") from error

    validate_message(message)

    return message