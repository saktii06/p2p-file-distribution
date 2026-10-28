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
    print("=" * 55)
    print("MULTI-PEER DOWNLOAD TEST")
    print("=" * 55)

    file_id = "multi_peer_test_file"
    downloader_id = "multi_peer_downloader"

    tracker = TrackerClient()
    servers = []

    with tempfile.TemporaryDirectory() as temp_folder:
        original_path = os.path.join(temp_folder, "original.txt")
        metainfo_path = os.path.join(temp_folder, "original.meta.json")
        downloaded_path = os.path.join(temp_folder, "downloaded.txt")

        try:
            # 1. Create a sample file and split it into pieces.
            print("\n1. Creating sample file...")

            original_data = (
                b"P2P multi-peer download test! " * 30000
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

            print("Original file size:", len(original_data), "bytes")
            print("Number of pieces:", number_of_pieces)

            assert number_of_pieces >= 3, (
                "The test requires at least three pieces."
            )

            print("PASS: Sample file created.")

            # 2. Assign different pieces to different peers.
            print("\n2. Starting partial peers...")

            peer_piece_assignments = [
                ("partial_peer_A", [0]),
                ("partial_peer_B", [1]),
                (
                    "partial_peer_C",
                    list(range(2, number_of_pieces))
                )
            ]

            for peer_id, initial_pieces in peer_piece_assignments:
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
                    peer_id + " failed to register with tracker."
                )

                print(
                    peer_id,
                    "started with pieces:",
                    initial_pieces
                )

            time.sleep(0.3)

            # 3. Discover the partial peers through the tracker.
            print("\n3. Discovering peers through tracker...")

            discovered_peers = tracker.get_peers(
                file_id=file_id,
                peer_id=downloader_id
            )

            discovered_ids = {
                peer["peer_id"] for peer in discovered_peers
            }

            expected_ids = {
                "partial_peer_A",
                "partial_peer_B",
                "partial_peer_C"
            }

            assert expected_ids.issubset(discovered_ids), (
                "The tracker did not return all three partial peers."
            )

            print("PASS: All three partial peers discovered.")

            # 4. Download the file using the discovered peers.
            print("\n4. Starting multi-peer download...")

            downloader = PeerDownloader(
                peer_id=downloader_id,
                file_id=file_id,
                metainfo_path=metainfo_path,
                output_path=downloaded_path,
                strategy="sequential"
            )

            success = downloader.download()

            assert success, (
                "The downloader could not reconstruct the file."
            )

            print("PASS: Download completed.")

            # 5. Verify that the reconstructed file is identical.
            print("\n5. Verifying downloaded file...")

            with open(downloaded_path, "rb") as file:
                downloaded_data = file.read()

            assert downloaded_data == original_data, (
                "The downloaded file does not match the original."
            )

            print("PASS: Downloaded file matches the original.")

            print("\n" + "=" * 55)
            print("ALL MULTI-PEER DOWNLOAD TESTS PASSED!")
            print("=" * 55)

        finally:
            # Stop all peers and clean up their tracker registrations.
            for server in reversed(servers):
                try:
                    server.stop()
                except OSError as error:
                    print("Server cleanup warning:", error)


if __name__ == "__main__":
    main()
