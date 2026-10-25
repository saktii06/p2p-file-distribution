import json
import socket


class TrackerClient:
    """Handles communication between a peer and the tracker."""

    def __init__(self, tracker_host="127.0.0.1", tracker_port=5000):
        self.tracker_host = tracker_host
        self.tracker_port = tracker_port

    def send_request(self, request):
        """Send a JSON request to the tracker and receive its response."""

        with socket.create_connection(
            (self.tracker_host, self.tracker_port),
            timeout=10
        ) as connection:

            # Send the request as JSON followed by a newline.
            message = json.dumps(request) + "\n"
            connection.sendall(message.encode("utf-8"))

            # Receive the tracker's response.
            response_data = bytearray()

            while True:
                chunk = connection.recv(4096)

                if not chunk:
                    break

                response_data.extend(chunk)

                # The tracker uses newline-delimited JSON.
                if b"\n" in response_data:
                    break

            if not response_data:
                raise ConnectionError("No response received from tracker.")

            response_line = bytes(response_data).split(b"\n", 1)[0]
            response = json.loads(response_line.decode("utf-8"))

            if response.get("status") != "success":
                raise RuntimeError(
                    response.get("message", "Tracker request failed.")
                )

            return response

    def register_peer(
        self,
        peer_id,
        file_id,
        host,
        port,
        pieces
    ):
        """Register a peer and its available pieces."""

        request = {
            "action": "register",
            "peer_id": peer_id,
            "file_id": file_id,
            "host": host,
            "port": port,
            "pieces": pieces
        }

        response = self.send_request(request)

        print(f"[{peer_id}] Registered with tracker.")

        return response

    def update_pieces(self, peer_id, file_id, pieces):
        """Update the pieces currently available at a peer."""

        request = {
            "action": "update_pieces",
            "peer_id": peer_id,
            "file_id": file_id,
            "pieces": sorted(set(pieces))
        }

        response = self.send_request(request)

        print(f"[{peer_id}] Updated available pieces with tracker.")

        return response

    def get_peers(self, file_id, peer_id=None):
        """Find other peers sharing the same file."""

        request = {
            "action": "get_peers",
            "file_id": file_id
        }

        if peer_id is not None:
            request["peer_id"] = peer_id

        response = self.send_request(request)

        return response["peers"]

    def unregister_peer(self, peer_id, file_id):
        """Remove a peer from the tracker."""

        request = {
            "action": "unregister",
            "peer_id": peer_id,
            "file_id": file_id
        }

        response = self.send_request(request)

        print(f"[{peer_id}] Unregistered from tracker.")

        return response

    def get_stats(self):
        """Retrieve tracker statistics."""

        request = {
            "action": "stats"
        }

        return self.send_request(request)