from peer.tracker_client import TrackerClient

tracker = TrackerClient()

peers = tracker.get_peers(
    file_id="sample_file",
    peer_id="test_peer"
)

print("Peers registered for sample_file:")

for peer in peers:
    print(peer)

assert any(
    peer["peer_id"] == "peer_A"
    for peer in peers
), "Peer A was not found in the tracker!"

print("\nPASS: Actual peer registration verified.")