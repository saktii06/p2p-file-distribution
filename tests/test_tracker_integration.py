import os
import sys
import time
import tempfile

project_folder = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

sys.path.insert(0, project_folder)

from peer.peer_server import PeerServer
from peer.peer_downloader import PeerDownloader
from peer.file_manager import split_file, create_metainfo, save_metainfo
from peer.tracker_client import TrackerClient


def main():
    print("=" * 50)
    print("TRACKER INTEGRATION TEST")
    print("=" * 50)

    tracker = TrackerClient()
    file_id = "integration_test_file"
    peer_id = "integration_seeder"

    server = None
    registered = False

    with tempfile.TemporaryDirectory() as temp_folder:
        original_path = os.path.join(temp_folder, "original.txt")
        metainfo_path = os.path.join(temp_folder, "original.meta.json")
        downloaded_path = os.path.join(temp_folder, "downloaded.txt")

        # 1. Create a sample file.
        print("\n1. Creating sample file...")

        original_data = b"P2P tracker integration test! " * 30000

        with open(original_path, "wb") as file:
            file.write(original_data)

        pieces, piece_hashes = split_file(original_path)

        metainfo = create_metainfo(original_path, piece_hashes)
        save_metainfo(metainfo, metainfo_path)

        print(f"Original file size: {len(original_data)} bytes")
        print(f"Number of pieces: {len(pieces)}")
        print("PASS: Sample file and metainfo created.")

        try:
            # 2. Start and register the seeder.
            print("\n2. Starting seeder with tracker integration...")

            server = PeerServer(
                peer_id=peer_id,
                file_id=file_id,
                file_path=original_path,
                host="127.0.0.1",
                port=0,
                use_tracker=True
            )

            server.start()
            registered = server.tracker_registered

            assert registered, "Seeder did not register with tracker."

            print("PASS: Seeder registered with tracker.")

            # Give the server time to begin accepting connections.
            time.sleep(0.2)

            # 3. Verify that the tracker can discover the seeder.
            print("\n3. Discovering seeder through tracker...")

            discovered_peers = tracker.get_peers(
                file_id=file_id,
                peer_id="integration_downloader"
            )

            seeder_info = next(
                (
                    peer for peer in discovered_peers
                    if peer["peer_id"] == peer_id
                ),
                None
            )

            assert seeder_info is not None, (
                "Seeder was not found through the tracker."
            )

            print("Discovered seeder:", seeder_info["peer_id"])
            print("Seeder address:", seeder_info["host"])
            print("Seeder port:", seeder_info["port"])
            print("PASS: Seeder discovered.")

            # 4. Download without manually specifying the seeder address.
            print("\n4. Downloading through tracker discovery...")

            downloader = PeerDownloader(
                peer_id="integration_downloader",
                file_id=file_id,
                metainfo_path=metainfo_path,
                output_path=downloaded_path,
                strategy="sequential"
            )

            success = downloader.download()

            assert success, "Tracker-based download failed."

            print("PASS: Download completed.")

            # 5. Compare the downloaded file with the original.
            print("\n5. Verifying reconstructed file...")

            with open(downloaded_path, "rb") as file:
                downloaded_data = file.read()

            assert downloaded_data == original_data, (
                "Downloaded file differs from the original."
            )

            print("PASS: Downloaded file matches the original.")
            print(
                f"Pieces verified: {downloader.pieces_downloaded}"
            )

            print("\n" + "=" * 50)
            print("ALL TRACKER INTEGRATION TESTS PASSED!")
            print("=" * 50)

        finally:
            # Always stop the server and remove its registration.
            if server is not None:
                server.stop()

            # If startup registered the peer but cleanup did not remove
            # it, attempt a final cleanup.
            if registered:
                try:
                    remaining_peers = tracker.get_peers(
                        file_id=file_id,
                        peer_id="integration_downloader"
                    )

                    if any(
                        peer["peer_id"] == peer_id
                        for peer in remaining_peers
                    ):
                        tracker.unregister_peer(peer_id, file_id)

                except (OSError, ValueError, RuntimeError) as error:
                    print("Tracker cleanup warning:", error)


if __name__ == "__main__":
    main()