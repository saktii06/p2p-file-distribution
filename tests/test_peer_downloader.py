import os
import sys
import json
import time
import tempfile
import threading

project_folder = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

sys.path.insert(0, project_folder)

from peer.peer_server import PeerServer
from peer.peer_downloader import PeerDownloader
from peer.file_manager import split_file, create_metainfo, save_metainfo


def main():
    print("=" * 45)
    print("PEER DOWNLOADER TESTS")
    print("=" * 45)

    with tempfile.TemporaryDirectory() as temp_folder:

        # Create a sample file large enough to contain multiple pieces.
        original_path = os.path.join(
            temp_folder,
            "original.txt"
        )

        sample_data = (
            b"Hello P2P File Distribution! " * 30000
        )

        with open(original_path, "wb") as file:
            file.write(sample_data)

        print("\n1. Creating metainfo...")

        pieces, piece_hashes = split_file(original_path)

        metainfo = create_metainfo(
            original_path,
            piece_hashes
        )

        metainfo_path = os.path.join(
            temp_folder,
            "original.txt.meta.json"
        )

        save_metainfo(metainfo, metainfo_path)

        print(f"Original file size: {len(sample_data)} bytes")
        print(f"Number of pieces: {len(pieces)}")
        print("PASS: Metainfo created.")

        print("\n2. Starting seeder...")

        server = PeerServer(
            peer_id="peer_A",
            file_id="sample-file",
            file_path=original_path,
            port=0
        )

        server.start()

        try:
            # Give the server thread a moment to start.
            time.sleep(0.2)

            print("\n3. Downloading the file...")

            downloaded_path = os.path.join(
                temp_folder,
                "downloaded.txt"
            )

            downloader = PeerDownloader(
                peer_id="peer_B",
                file_id="sample-file",
                host="127.0.0.1",
                port=server.port,
                metainfo_path=metainfo_path,
                output_path=downloaded_path,
                strategy="sequential"
            )

            success = downloader.download()

            assert success, "Downloader reported failure."

            print("\n4. Comparing original and downloaded files...")

            with open(original_path, "rb") as file:
                original_data = file.read()

            with open(downloaded_path, "rb") as file:
                downloaded_data = file.read()

            assert downloaded_data == original_data

            print("PASS: Downloaded file matches the original.")
            print(f"Verified pieces: {downloader.pieces_downloaded}")

            print("\n" + "=" * 45)
            print("ALL PEER DOWNLOADER TESTS PASSED!")
            print("=" * 45)

        finally:
            server.stop()


if __name__ == "__main__":
    main()