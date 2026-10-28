import socket
import threading
import os

from peer.peer_protocol import (
    create_handshake,
    create_bitfield,
    create_have,
    create_piece,
    receive_message,
    send_message
)

from peer.file_manager import split_file, verify_piece
from peer.tracker_client import TrackerClient


class PeerServer:

    def __init__(
        self,
        peer_id,
        file_id,
        file_path,
        host="127.0.0.1",
        port=0,
        use_tracker=False,
        initial_pieces=None
    ):
        self.peer_id = peer_id
        self.file_id = file_id
        self.file_path = file_path
        self.host = host
        self.port = port

        # Load file pieces and calculate their hashes.
        self.pieces, self.piece_hashes = split_file(file_path)

        # If initial_pieces is not provided, this peer
        # starts with the complete file.
        if initial_pieces is None:
            self.available_pieces = set(range(len(self.pieces)))

        else:
            # Store only the pieces this peer initially owns.
            self.available_pieces = set(initial_pieces)

            # Validate the supplied piece indexes.
            for index in self.available_pieces:
                if not isinstance(index, int) or isinstance(index, bool):
                    raise ValueError("Piece indexes must be integers.")

                if index < 0 or index >= len(self.pieces):
                    raise ValueError(
                        f"Invalid piece index: {index}"
                    )

            # Remove data for pieces this peer does not own.
            for index in range(len(self.pieces)):
                if index not in self.available_pieces:
                    self.pieces[index] = None

        # Protect piece storage when multiple threads access it.
        self.pieces_lock = threading.Lock()

        # Store active peer connections.
        self.peer_connections = []
        self.connections_lock = threading.Lock()

        # Configure tracker communication.
        self.use_tracker = use_tracker
        self.tracker_client = TrackerClient() if use_tracker else None
        self.tracker_registered = False

        # Track server status.
        self.running = False
        self.server_socket = None

        # Keep track of client-handler threads.
        self.client_threads = []

    def start(self):
        """Start the peer server and register with the tracker."""

        self.server_socket = socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM
        )

        self.server_socket.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_REUSEADDR,
            1
        )

        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(10)

            # Get the actual port assigned by the operating system.
            self.port = self.server_socket.getsockname()[1]

            print(
                f"[{self.peer_id}] Peer server listening "
                f"on {self.host}:{self.port}"
            )

            # Register the peer and its available pieces.
            if self.use_tracker:
                self.tracker_client.register_peer(
                    peer_id=self.peer_id,
                    file_id=self.file_id,
                    host=self.host,
                    port=self.port,
                    pieces=sorted(self.available_pieces)
                )

                self.tracker_registered = True

            self.running = True

            # Accept incoming connections in a separate thread.
            self.accept_thread = threading.Thread(
                target=self.accept_connections,
                daemon=True
            )

            self.accept_thread.start()

        except Exception:
            self.running = False

            if self.server_socket:
                self.server_socket.close()
                self.server_socket = None

            raise

    def add_piece(self, piece_index, piece_data):
        """Verify and store a newly downloaded piece."""

        # Check whether the piece index is valid.
        if (
            not isinstance(piece_index, int)
            or isinstance(piece_index, bool)
            or piece_index < 0
            or piece_index >= len(self.pieces)
        ):
            raise ValueError("Invalid piece index.")

        # Verify the piece before storing it.
        if not verify_piece(
            piece_data,
            self.piece_hashes[piece_index]
        ):
            raise ValueError("Piece verification failed.")

        # Store the piece and update availability safely.
        with self.pieces_lock:
            self.pieces[piece_index] = piece_data
            self.available_pieces.add(piece_index)

            available_pieces = sorted(self.available_pieces)

        print(
            f"[{self.peer_id}] Piece {piece_index} "
            "stored and verified."
        )

        # Notify connected peers about the new piece.
        self.notify_have(piece_index)

        # Update the tracker with the current piece list.
        if self.use_tracker and self.tracker_registered:
            try:
                self.tracker_client.update_pieces(
                    peer_id=self.peer_id,
                    file_id=self.file_id,
                    pieces=available_pieces
                )

            except (
                OSError,
                ConnectionError,
                RuntimeError,
                ValueError
            ) as error:
                print(
                    f"[{self.peer_id}] Could not update tracker: "
                    f"{error}"
                )

        return True

    def notify_have(self, piece_index):
        """Notify connected peers that a new piece is available."""

        message = create_have(piece_index)

        # Copy the connection list while holding its lock.
        with self.connections_lock:
            connections = list(self.peer_connections)

        for connection in connections:
            try:
                send_message(connection, message)

            except (OSError, ConnectionError):
                # A connection may have closed during notification.
                pass

    def accept_connections(self):
        """Accept connections and create a thread for each peer."""

        while self.running:
            try:
                connection, address = self.server_socket.accept()

                print(
                    f"[{self.peer_id}] Connection received from "
                    f"{address}"
                )

                # Keep track of this connection.
                with self.connections_lock:
                    self.peer_connections.append(connection)

                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(connection, address),
                    daemon=True
                )

                self.client_threads.append(client_thread)
                client_thread.start()

            except OSError:
                # The socket may have closed during shutdown.
                break

    def handle_client(self, connection, address):
        """Handle communication with one connected peer."""

        remote_peer_id = None

        try:
            # The first message must be a handshake.
            message = receive_message(connection)

            if message["type"] != "HANDSHAKE":
                raise ValueError(
                    "First message must be a handshake."
                )

            remote_peer_id = message["peer_id"]
            remote_file_id = message["file_id"]

            # Both peers must be sharing the same file.
            if remote_file_id != self.file_id:
                print(
                    f"[{self.peer_id}] Rejected peer with "
                    "a different file ID."
                )
                return

            print(
                f"[{self.peer_id}] Handshake received from "
                f"{remote_peer_id}"
            )

            # Send our handshake.
            send_message(
                connection,
                create_handshake(self.peer_id, self.file_id)
            )

            # Send the pieces currently available.
            with self.pieces_lock:
                available_pieces = sorted(self.available_pieces)

            send_message(
                connection,
                create_bitfield(available_pieces)
            )

            # Process incoming messages.
            while self.running:
                message = receive_message(connection)
                message_type = message["type"]

                if message_type == "REQUEST":
                    piece_index = message["piece_index"]

                    # Validate the requested piece index.
                    if (
                        not isinstance(piece_index, int)
                        or isinstance(piece_index, bool)
                        or piece_index < 0
                        or piece_index >= len(self.pieces)
                    ):
                        print(
                            f"[{self.peer_id}] Invalid piece request: "
                            f"{piece_index}"
                        )
                        continue

                    # Check availability and retrieve the piece safely.
                    with self.pieces_lock:
                        if piece_index not in self.available_pieces:
                            print(
                                f"[{self.peer_id}] Does not have piece "
                                f"{piece_index}"
                            )
                            continue

                        piece_data = self.pieces[piece_index]

                    # Send the requested piece.
                    send_message(
                        connection,
                        create_piece(piece_index, piece_data)
                    )

                    print(
                        f"[{self.peer_id}] Sent piece "
                        f"{piece_index} to {remote_peer_id}"
                    )

                elif message_type == "CANCEL":
                    print(
                        f"[{self.peer_id}] Received cancellation "
                        f"for piece {message['piece_index']}"
                    )

                elif message_type == "HAVE":
                    print(
                        f"[{self.peer_id}] Peer {remote_peer_id} "
                        f"has piece {message['piece_index']}"
                    )

                elif message_type == "BITFIELD":
                    print(
                        f"[{self.peer_id}] Received bitfield "
                        f"from {remote_peer_id}"
                    )

                elif message_type == "PIECE":
                    print(
                        f"[{self.peer_id}] Received an unexpected "
                        "PIECE message."
                    )

                elif message_type == "HANDSHAKE":
                    print(
                        f"[{self.peer_id}] Received an unexpected "
                        "second handshake."
                    )

        except (ConnectionError, OSError) as error:
            print(
                f"[{self.peer_id}] Connection with {address} closed: "
                f"{error}"
            )

        except (ValueError, KeyError) as error:
            print(
                f"[{self.peer_id}] Invalid peer communication: "
                f"{error}"
            )

        finally:
            # Remove the connection from the active connection list.
            with self.connections_lock:
                if connection in self.peer_connections:
                    self.peer_connections.remove(connection)

            connection.close()

    def stop(self):
        """Stop the server and unregister from the tracker."""

        self.running = False

        # Close the listening socket.
        if self.server_socket:
            self.server_socket.close()
            self.server_socket = None

        # Close active peer connections.
        with self.connections_lock:
            connections = list(self.peer_connections)

        for connection in connections:
            try:
                connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

            try:
                connection.close()
            except OSError:
                pass

        # Unregister this peer from the tracker.
        if self.tracker_registered:
            try:
                self.tracker_client.unregister_peer(
                    peer_id=self.peer_id,
                    file_id=self.file_id
                )

            except (OSError, ValueError, RuntimeError) as error:
                print(
                    f"[{self.peer_id}] Could not unregister "
                    f"from tracker: {error}"
                )

            finally:
                self.tracker_registered = False

        print(f"[{self.peer_id}] Peer server stopped.")


if __name__ == "__main__":

    file_path = input(
        "Enter the path of the file to share: "
    ).strip()

    if not os.path.isfile(file_path):
        print("Error: File does not exist.")

    else:
        peer_id = input("Enter peer ID: ").strip()
        file_id = input("Enter file ID: ").strip()

        server = PeerServer(
            peer_id=peer_id,
            file_id=file_id,
            file_path=file_path,
            host="127.0.0.1",
            port=6000,
            use_tracker=True
        )

        try:
            server.start()

            print(
                "Peer registered. Press Ctrl+C to stop the server."
            )

            while True:
                threading.Event().wait(1)

        except KeyboardInterrupt:
            pass

        except (OSError, ValueError, RuntimeError) as error:
            print(f"Could not start peer server: {error}")

        finally:
            server.stop()