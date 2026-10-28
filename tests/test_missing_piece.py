import os
import sys
import tempfile
import time

project_folder = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

sys.path.insert(0, project_folder)

from peer.peer_server import PeerServer
from peer.peer_downloader import PeerDownloader
from peer.file_manager import (
    split_file,
    create_metainfo,
    save_metainfo
)


def main():
    print("=" * 55)
    print("MISSING PIECE TEST")
    print("=" * 55)

    file_id = "missing_piece_test_file"
    downloader_id = "missing_piece_downloader"

    servers = []

    with tempfile.TemporaryDirectory() as temp_folder:
        original_path = os.path.join(
            temp_folder, "original.txt"
        )
        metainfo_path = os.path.join(
            temp_folder, "original.meta.json"
        )
        downloaded_path = os.path.join(
            temp_folder, "downloaded.txt"
        )

        try:
            # 1. Create a sample file.
            print("\n1. Creating sample file...")

            original_data = (
                b"Missing piece test data! " * 50000
            )

            with open(original_path, "wb") as file:
                file.write(original_data)

            pieces, piece_hashes = split_file(original_path)

            metainfo = create_metainfo(
                original_path,
                piece_hashes
            )

            save_metainfo(metainfo, metainfo_path)

            number_of_pieces = len(pieces)

            print("Original file size:", len(original_data))
            print("Number of pieces:", number_of_pieces)

            assert number_of_pieces >= 4, (
                "The test requires at least four pieces."
            )

            print("PASS: Sample file created.")

            # 2. Leave the last piece unavailable.
            print("\n2. Starting partial peers...")

            assignments = [
                ("missing_peer_A", [0]),
                ("missing_peer_B", [1]),
                (
                    "missing_peer_C",
                    list(range(2, number_of_pieces - 1))
                )
            ]

            for peer_id, initial_pieces in assignments:
                server = PeerServer(
                    peer_id=peer_id,
                    file_id=file_id,
                    file_path=original_path,
                    host="127.0.0.1",
                    port=0,
                    use_tracker=True,
                    initial_pieces=initial_pieces
                )

                server.start()
                servers.append(server)

                assert server.tracker_registered, (
                    peer_id + " failed to register."
                )

                print(
                    peer_id,
                    "provides pieces:",
                    initial_pieces
                )

            missing_piece_index = number_of_pieces - 1

            # Allow tracker registrations to become available.
            time.sleep(0.2)

            # 3. Attempt to download the incomplete file.
            print("\n3. Attempting download with a missing piece...")
            print(
                "Intentionally unavailable piece:",
                missing_piece_index
            )

            downloader = PeerDownloader(
                peer_id=downloader_id,
                file_id=file_id,
                metainfo_path=metainfo_path,
                output_path=downloaded_path,
                strategy="sequential"
            )

            success = downloader.download()

            # The downloader must reject an incomplete swarm.
            assert not success, (
                "The downloader unexpectedly succeeded even though "
                "a required piece was unavailable."
            )

            print(
                "PASS: Downloader correctly rejected the incomplete swarm."
            )

            print("\n" + "=" * 55)
            print("ALL MISSING PIECE TESTS PASSED!")
            print("=" * 55)

        finally:
            # 4. Stop peers and clean up registrations.
            for server in reversed(servers):
                try:
                    server.stop()
                except OSError as error:
                    print("Server cleanup warning:", error)


if __name__ == "__main__":
    main()