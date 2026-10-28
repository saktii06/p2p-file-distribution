import os
import sys
import socket
import tempfile
import time

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
    print("PEER FAILURE HANDLING TEST")
    print("=" * 55)

    file_id = "peer_failure_test_file"
    downloader_id = "peer_failure_downloader"

    servers = []
    tracker = TrackerClient()

    # Reserve a port and release it so the test has an unavailable
    # peer address. The port should remain unused during this test.
    temporary_socket = socket.socket()
    temporary_socket.bind(("127.0.0.1", 0))
    unavailable_port = temporary_socket.getsockname()[1]
    temporary_socket.close()

    with tempfile.TemporaryDirectory() as temp_folder:
        original_path = os.path.join(temp_folder, "original.txt")
        metainfo_path = os.path.join(temp_folder, "original.meta.json")
        downloaded_path = os.path.join(temp_folder, "downloaded.txt")

        try:
            # 1. Create a sample file.
            print("\n1. Creating sample file...")

            original_data = b"P2P failure handling test! " * 30000

            with open(original_path, "wb") as file:
                file.write(original_data)

            pieces, piece_hashes = split_file(original_path)

            metainfo = create_metainfo(original_path, piece_hashes)
            save_metainfo(metainfo, metainfo_path)

            number_of_pieces = len(pieces)

            assert number_of_pieces >= 3, (
                "The test requires at least three pieces."
            )

            print("PASS: Sample file created.")

            # 2. Start three available partial peers.
            print("\n2. Starting available peers...")

            assignments = [
                ("failure_peer_B", [0]),
                ("failure_peer_C", [1]),
                (
                    "failure_peer_D",
                    list(range(2, number_of_pieces))
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

            # 3. Register a peer address that is not listening.
            print("\n3. Registering an unavailable peer...")

            tracker.send_request({
                "action": "register",
                "peer_id": "failure_peer_A",
                "file_id": file_id,
                "host": "127.0.0.1",
                "port": unavailable_port,
                "pieces": [0]
            })

            print(
                "Unavailable peer registered at port:",
                unavailable_port
            )

            time.sleep(0.2)

            # 4. Run the downloader.
            print("\n4. Starting download...")

            downloader = PeerDownloader(
                peer_id=downloader_id,
                file_id=file_id,
                metainfo_path=metainfo_path,
                output_path=downloaded_path,
                strategy="sequential"
            )

            success = downloader.download()

            assert success, (
                "Download failed even though all pieces "
                "were available from other peers."
            )

            print("PASS: Download survived an unavailable peer.")

            # 5. Verify the reconstructed file.
            print("\n5. Verifying downloaded file...")

            with open(downloaded_path, "rb") as file:
                downloaded_data = file.read()

            assert downloaded_data == original_data, (
                "Downloaded file does not match the original."
            )

            print("PASS: Reconstructed file matches the original.")

            print("\n" + "=" * 55)
            print("ALL PEER FAILURE TESTS PASSED!")
            print("=" * 55)

        finally:
            # Stop peers and remove their tracker registrations.
            for server in reversed(servers):
                try:
                    server.stop()
                except OSError as error:
                    print("Server cleanup warning:", error)

            try:
                tracker.unregister_peer(
                    "failure_peer_A",
                    file_id
                )
            except (OSError, ValueError, RuntimeError) as error:
                print("Unavailable peer cleanup warning:", error)


if __name__ == "__main__":
    main()
