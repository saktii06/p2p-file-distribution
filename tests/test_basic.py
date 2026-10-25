import json
import socket

TRACKER_HOST = "127.0.0.1"
TRACKER_PORT = 5000


def send_request(request):
    """Sends a request to the tracker and receives its response."""

    with socket.create_connection(
        (TRACKER_HOST, TRACKER_PORT),
        timeout=5
    ) as connection:

        file = connection.makefile("rwb")

        message = json.dumps(request) + "\n"

        file.write(message.encode("utf-8"))
        file.flush()

        response = file.readline()

        if not response:
            raise RuntimeError("Tracker returned an empty response.")

        return json.loads(response.decode("utf-8"))


def main():
    file_id = "sample-file-001"

    # Register Peer A
    peer_a = {
        "action": "register",
        "peer_id": "peer_A",
        "file_id": file_id,
        "host": "127.0.0.1",
        "port": 6001,
        "pieces": [0, 1, 2]
    }

    print("Registering Peer A...")
    print(send_request(peer_a))

    # Register Peer B
    peer_b = {
        "action": "register",
        "peer_id": "peer_B",
        "file_id": file_id,
        "host": "127.0.0.1",
        "port": 6002,
        "pieces": [0]
    }

    print("\nRegistering Peer B...")
    print(send_request(peer_b))

    # Ask the tracker to find other peers
    discovery_request = {
        "action": "get_peers",
        "peer_id": "peer_B",
        "file_id": file_id
    }

    print("\nDiscovering peers...")
    result = send_request(discovery_request)

    print(json.dumps(result, indent=4))

    # Verify that Peer B discovers Peer A
    discovered_ids = [
        peer["peer_id"]
        for peer in result.get("peers", [])
    ]

    assert "peer_A" in discovered_ids
    assert "peer_B" not in discovered_ids

    # Display tracker statistics
    print("\nTracker statistics:")
    print(send_request({"action": "stats"}))

    print("\nALL TRACKER TESTS PASSED!")


if __name__ == "__main__":
    main()