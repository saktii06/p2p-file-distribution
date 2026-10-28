import json
import os
import socket

from peer.tracker_client import TrackerClient

from peer.peer_protocol import (
    create_handshake,
    create_request,
    receive_message,
    send_message,
    decode_piece
)

from peer.file_manager import verify_piece, reconstruct_file
from peer.piece_manager import PieceManager


class PeerDownloader:

    def __init__(
        self,
        peer_id,
        file_id,
        host=None,
        port=None,
        metainfo_path=None,
        output_path=None,
        strategy="sequential",
        tracker_host="127.0.0.1",
        tracker_port=5000
    ):
        self.peer_id = peer_id
        self.file_id = file_id
        self.metainfo_path = metainfo_path
        self.output_path = output_path
        self.strategy = strategy

        self.tracker_client = TrackerClient(
            tracker_host=tracker_host,
            tracker_port=tracker_port
        )

        # Optional direct connection for compatibility with old tests.
        self.host = host
        self.port = port

        with open(metainfo_path, "r", encoding="utf-8") as file:
            self.metainfo = json.load(file)

        self.total_pieces = self.metainfo["number_of_pieces"]
        self.piece_hashes = self.metainfo["piece_hashes"]

        self.downloaded_pieces = {}

        self.pieces_requested = 0
        self.pieces_downloaded = 0

    def get_peers_from_tracker(self):
        """Find peers sharing this file through the tracker."""

        print("\nSearching for peers through the tracker...")

        peers = self.tracker_client.get_peers(
            file_id=self.file_id,
            peer_id=self.peer_id
        )

        if not peers:
            raise ValueError("No other peers found for this file.")

        print(f"Tracker returned {len(peers)} peer(s).")

        return peers

    def get_seeder_from_tracker(self):
        """Find one peer that has the complete file."""

        peers = self.get_peers_from_tracker()

        for peer in peers:
            available = set(peer.get("pieces", []))

            if len(available) == self.total_pieces:
                print(
                    f"Selected seeder: {peer['peer_id']} "
                    f"at {peer['host']}:{peer['port']}"
                )
                return peer

        raise ValueError("No complete seeder found.")

    def connect_to_peer(self, peer):
        """Connect to a peer and check which pieces it has."""

        connection = socket.create_connection(
            (peer["host"], peer["port"]),
            timeout=10
        )

        connection.settimeout(30)

        try:
            # Introduce ourselves to the peer.
            send_message(
                connection,
                create_handshake(self.peer_id, self.file_id)
            )

            handshake = receive_message(connection)

            if handshake["type"] != "HANDSHAKE":
                raise ValueError("Invalid handshake received.")

            if handshake["file_id"] != self.file_id:
                raise ValueError("Peer has a different file ID.")

            # Find out which pieces the peer actually possesses.
            bitfield = receive_message(connection)

            if bitfield["type"] != "BITFIELD":
                raise ValueError("Expected a bitfield from peer.")

            available_pieces = set(bitfield["pieces"])

            # The peer may be registered with stale piece information.
            # The bitfield received from the peer is the current source
            # of truth for this connection.
            print(
                f"Connected to {handshake['peer_id']}; "
                f"it has {len(available_pieces)} piece(s)."
            )

            return connection, available_pieces

        except Exception:
            connection.close()
            raise

    def download_piece(self, connection, piece_index):
        """Request one piece and verify its contents."""

        self.pieces_requested += 1

        send_message(
            connection,
            create_request(piece_index)
        )

        response = receive_message(connection)

        if response["type"] != "PIECE":
            raise ValueError("Expected a PIECE response from peer.")

        if response["piece_index"] != piece_index:
            raise ValueError("Received a different piece than requested.")

        piece_data = decode_piece(response)

        expected_hash = self.piece_hashes[piece_index]

        if not verify_piece(piece_data, expected_hash):
            raise ValueError(
                f"Hash verification failed for piece {piece_index}."
            )

        self.downloaded_pieces[piece_index] = piece_data
        self.pieces_downloaded += 1

        print(f"Piece {piece_index} received and verified.")

    def download(self):
        """Download a file using one or more peers."""

        print("=" * 45)
        print("P2P PEER DOWNLOADER")
        print("=" * 45)

        print(f"File: {self.metainfo['filename']}")
        print(f"Selection strategy: {self.strategy}")

        connections = []

        try:
            # Prepare the list of peers to use.
            if self.host is not None and self.port is not None:
                peers = [{
                    "peer_id": "direct_peer",
                    "host": self.host,
                    "port": self.port
                }]
            else:
                peers = self.get_peers_from_tracker()

            # Connect to the peers and collect their available pieces.
            peer_connections = []
            piece_availability = {
                index: [] for index in range(self.total_pieces)
            }

            for peer in peers:
                try:
                    connection, available_pieces = self.connect_to_peer(
                        peer
                    )

                    connections.append(connection)

                    peer_connections.append({
                        "peer": peer,
                        "connection": connection,
                        "pieces": available_pieces
                    })

                    for piece_index in available_pieces:
                        if 0 <= piece_index < self.total_pieces:
                            piece_availability[piece_index].append(
                                peer["peer_id"]
                            )

                except (OSError, ValueError, RuntimeError) as error:
                    print(
                        f"Could not connect to {peer.get('peer_id', 'peer')}: "
                        f"{error}"
                    )

            if not peer_connections:
                raise ValueError("Could not connect to any peers.")

            # Check that all pieces are available somewhere in the swarm.
            for piece_index in range(self.total_pieces):
                if not piece_availability[piece_index]:
                    raise ValueError(
                        f"No connected peer has piece {piece_index}."
                    )

            piece_manager = PieceManager(self.total_pieces)

            # Count how many peers have each piece.
            availability_counts = {
                index: len(piece_availability[index])
                for index in range(self.total_pieces)
            }

            print("\nStarting multi-peer download...\n")

            while not piece_manager.is_complete():

                piece_index = piece_manager.select_piece(
                    self.strategy,
                    availability_counts
                )

                # Choose a peer that has the selected piece.
                selected_peer = None

                for peer_info in peer_connections:
                    if piece_index in peer_info["pieces"]:
                        selected_peer = peer_info
                        break

                if selected_peer is None:
                    raise ValueError(
                        f"No peer available for piece {piece_index}."
                    )

                peer_name = selected_peer["peer"]["peer_id"]

                print(
                    f"Requesting piece {piece_index} from {peer_name}..."
                )

                self.download_piece(
                    selected_peer["connection"],
                    piece_index
                )

                piece_manager.add_piece(piece_index)

            print("\nAll pieces downloaded successfully.")

            # Close peer connections before reconstructing the file.
            for connection in connections:
                try:
                    connection.close()
                except OSError:
                    pass

            connections.clear()

            # Reconstruct the original file in the correct order.
            ordered_pieces = [
                self.downloaded_pieces[index]
                for index in range(self.total_pieces)
            ]

            output_folder = os.path.dirname(self.output_path)

            if output_folder:
                os.makedirs(output_folder, exist_ok=True)

            reconstruct_file(ordered_pieces, self.output_path)

            # Check the reconstructed file size.
            actual_size = os.path.getsize(self.output_path)
            expected_size = self.metainfo["file_size"]

            if actual_size != expected_size:
                raise ValueError(
                    f"File size mismatch: expected {expected_size}, "
                    f"received {actual_size}."
                )

            print("\n" + "=" * 45)
            print("DOWNLOAD COMPLETED SUCCESSFULLY!")
            print("=" * 45)

            print(f"Downloaded file: {self.output_path}")
            print(f"Pieces requested: {self.pieces_requested}")
            print(f"Pieces downloaded: {self.pieces_downloaded}")
            print(f"Final file size: {actual_size} bytes")

            return True

        except (
            OSError,
            ValueError,
            KeyError,
            IndexError,
            RuntimeError,
            ConnectionError
        ) as error:
            print(f"\nDownload failed: {error}")
            return False

        finally:
            # Always close remaining connections.
            for connection in connections:
                try:
                    connection.close()
                except OSError:
                    pass
