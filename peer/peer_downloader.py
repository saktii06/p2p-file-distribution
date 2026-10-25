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

        # Tracker connection.
        self.tracker_client = TrackerClient(
            tracker_host=tracker_host,
            tracker_port=tracker_port
        )

        # Optional direct connection for compatibility with old tests.
        self.host = host
        self.port = port

        # Load information about the original file.
        with open(metainfo_path, "r", encoding="utf-8") as file:
            self.metainfo = json.load(file)

        self.total_pieces = self.metainfo["number_of_pieces"]
        self.piece_hashes = self.metainfo["piece_hashes"]

        # Store downloaded pieces using their indexes.
        self.downloaded_pieces = {}

        # Download statistics.
        self.pieces_requested = 0
        self.pieces_downloaded = 0

    def get_seeder_from_tracker(self):
        """Discover a suitable seeder through the tracker."""

        print("\nSearching for peers through the tracker...")

        peers = self.tracker_client.get_peers(
            file_id=self.file_id,
            peer_id=self.peer_id
        )

        if not peers:
            raise ValueError(
                "No other peers found for this file."
            )

        print(f"Tracker returned {len(peers)} peer(s).")

        # Prefer a peer that possesses the complete file.
        for peer in peers:
            if len(peer.get("pieces", [])) == self.total_pieces:
                print(
                    f"Selected seeder: {peer['peer_id']} "
                    f"at {peer['host']}:{peer['port']}"
                )
                return peer

        raise ValueError(
            "No complete seeder found. "
            "Multi-peer downloading is not implemented yet."
        )

    def download(self):
        """Discover a seeder and download the file."""

        print("=" * 45)
        print("P2P PEER DOWNLOADER")
        print("=" * 45)

        print(f"File: {self.metainfo['filename']}")
        print(f"Selection strategy: {self.strategy}")

        try:
            # Find a seeder through the tracker if no address was supplied.
            if self.host is None or self.port is None:
                seeder = self.get_seeder_from_tracker()
                self.host = seeder["host"]
                self.port = seeder["port"]

            print(
                f"\nConnecting to seeder at "
                f"{self.host}:{self.port}..."
            )

            with socket.create_connection(
                (self.host, self.port),
                timeout=10
            ) as connection:

                connection.settimeout(30)

                # Introduce ourselves to the seeder.
                send_message(
                    connection,
                    create_handshake(self.peer_id, self.file_id)
                )

                # Receive the seeder's handshake.
                handshake = receive_message(connection)

                if handshake["type"] != "HANDSHAKE":
                    raise ValueError("Invalid handshake received.")

                if handshake["file_id"] != self.file_id:
                    raise ValueError("Seeder has a different file ID.")

                print(
                    f"Handshake successful with "
                    f"{handshake['peer_id']}."
                )

                # Receive the seeder's bitfield.
                bitfield = receive_message(connection)

                if bitfield["type"] != "BITFIELD":
                    raise ValueError("Expected a bitfield from seeder.")

                available_pieces = set(bitfield["pieces"])

                print(
                    f"Seeder has {len(available_pieces)} "
                    f"available pieces."
                )

                # Check that the seeder has the complete file.
                required_pieces = set(range(self.total_pieces))

                if not required_pieces.issubset(available_pieces):
                    raise ValueError(
                        "Seeder does not possess all required pieces."
                    )

                # Create a manager to select pieces.
                piece_manager = PieceManager(self.total_pieces)

                # At this stage, only one seeder is used.
                availability = {
                    index: 1 for index in available_pieces
                }

                print("\nStarting download...\n")

                while not piece_manager.is_complete():

                    piece_index = piece_manager.select_piece(
                        self.strategy,
                        availability
                    )

                    self.pieces_requested += 1

                    print(f"Requesting piece {piece_index}...")

                    # Request the selected piece.
                    send_message(
                        connection,
                        create_request(piece_index)
                    )

                    response = receive_message(connection)

                    if response["type"] != "PIECE":
                        raise ValueError(
                            "Expected a PIECE response from seeder."
                        )

                    if response["piece_index"] != piece_index:
                        raise ValueError(
                            "Received a different piece than requested."
                        )

                    piece_data = decode_piece(response)

                    # Verify the piece using its SHA-256 hash.
                    expected_hash = self.piece_hashes[piece_index]

                    if not verify_piece(piece_data, expected_hash):
                        raise ValueError(
                            f"Hash verification failed for piece "
                            f"{piece_index}."
                        )

                    print(
                        f"Piece {piece_index} received and verified."
                    )

                    self.downloaded_pieces[piece_index] = piece_data

                    piece_manager.add_piece(piece_index)

                    self.pieces_downloaded += 1

                print("\nAll pieces downloaded successfully.")

            # Reconstruct the file in the correct order.
            ordered_pieces = [
                self.downloaded_pieces[index]
                for index in range(self.total_pieces)
            ]

            output_folder = os.path.dirname(self.output_path)

            if output_folder:
                os.makedirs(output_folder, exist_ok=True)

            reconstruct_file(ordered_pieces, self.output_path)

            # Verify the reconstructed file size.
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
            RuntimeError
        ) as error:
            print(f"\nDownload failed: {error}")
            return False