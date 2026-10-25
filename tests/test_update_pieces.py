from peer.tracker_client import TrackerClient


def main():
    tracker = TrackerClient()

    peer_id = "update_test_peer"
    file_id = "update_test_file"

    try:
        print("1. Registering peer...")

        tracker.register_peer(
            peer_id=peer_id,
            file_id=file_id,
            host="127.0.0.1",
            port=6005,
            pieces=[0]
        )

        print("\n2. Updating available pieces...")

        tracker.update_pieces(
            peer_id=peer_id,
            file_id=file_id,
            pieces=[0, 1, 2]
        )

        print("\n3. Checking tracker information...")

        peers = tracker.get_peers(file_id)

        peer = next(
            p for p in peers
            if p["peer_id"] == peer_id
        )

        print("Pieces recorded by tracker:", peer["pieces"])

        assert peer["pieces"] == [0, 1, 2]

        print("\nPASS: Piece availability updated successfully.")

    finally:
        tracker.unregister_peer(peer_id, file_id)


if __name__ == "__main__":
    main()