from peer.tracker_client import TrackerClient


def main():
    print("=" * 45)
    print("TRACKER CLIENT TESTS")
    print("=" * 45)

    tracker = TrackerClient()

    file_id = "test_file_001"

    # Register the first peer.
    print("\n1. Registering Peer A...")

    tracker.register_peer(
        peer_id="peer_A",
        file_id=file_id,
        host="127.0.0.1",
        port=6001,
        pieces=[0, 1, 2, 3]
    )

    print("PASS: Peer A registered.")

    # Register the second peer.
    print("\n2. Registering Peer B...")

    tracker.register_peer(
        peer_id="peer_B",
        file_id=file_id,
        host="127.0.0.1",
        port=6002,
        pieces=[]
    )

    print("PASS: Peer B registered.")

    # Ask the tracker to find other peers.
    print("\n3. Discovering peers from Peer B...")

    peers = tracker.get_peers(
        file_id=file_id,
        peer_id="peer_B"
    )

    peer_ids = [peer["peer_id"] for peer in peers]

    print("Peers found:", peer_ids)

    assert "peer_A" in peer_ids
    assert "peer_B" not in peer_ids

    print("PASS: Peer B discovered Peer A.")

    # Check tracker statistics.
    print("\n4. Checking tracker statistics...")

    stats = tracker.get_stats()

    print("Files tracked:", stats["files_tracked"])
    print("Registered peers:", stats["registered_peers"])

    assert stats["registered_peers"] >= 2

    print("PASS: Tracker statistics received.")

    # Remove the test peers.
    print("\n5. Cleaning up test registrations...")

    tracker.unregister_peer("peer_A", file_id)
    tracker.unregister_peer("peer_B", file_id)

    print("\n" + "=" * 45)
    print("ALL TRACKER CLIENT TESTS PASSED!")
    print("=" * 45)


if __name__ == "__main__":
    main()