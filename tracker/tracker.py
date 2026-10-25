import json
import socketserver
import threading

# Tracker configuration
HOST = "127.0.0.1"
PORT = 5000

# Stores information about files and their peers
peer_registry = {}

# Prevents simultaneous conflicting updates
registry_lock = threading.Lock()


class TrackerHandler(socketserver.StreamRequestHandler):

    def handle(self):
        """Receives and processes one request from a peer."""

        try:
            request_line = self.rfile.readline()

            if not request_line:
                return

            request = json.loads(request_line.decode("utf-8"))
            response = self.process_request(request)

        except (json.JSONDecodeError, UnicodeDecodeError):
            response = {
                "status": "error",
                "message": "Invalid request format."
            }

        except Exception as error:
            print("Error:", error)

            response = {
                "status": "error",
                "message": "Unable to process request."
            }

        self.wfile.write(
            (json.dumps(response) + "\n").encode("utf-8")
        )

    def process_request(self, request):
        """Identifies the requested operation."""

        action = request.get("action")

        if action == "register":
            return self.register_peer(request)

        elif action == "get_peers":
            return self.get_peers(request)

        elif action == "update_pieces":
            return self.update_pieces(request)

        elif action == "unregister":
            return self.unregister_peer(request)

        elif action == "stats":
            return self.get_stats()

        return {
            "status": "error",
            "message": "Unknown action."
        }

    def register_peer(self, request):
        """Registers a peer that has a particular file."""

        peer_id = request.get("peer_id")
        file_id = request.get("file_id")
        host = request.get("host")
        port = request.get("port")
        pieces = request.get("pieces", [])

        if not peer_id or not file_id or not host:
            return {
                "status": "error",
                "message": "peer_id, file_id and host are required."
            }

        if type(port) is not int or not 1 <= port <= 65535:
            return {
                "status": "error",
                "message": "A valid port number is required."
            }

        if (
            not isinstance(pieces, list)
            or any(type(piece) is not int or piece < 0 for piece in pieces)
        ):
            return {
                "status": "error",
                "message": "pieces must contain non-negative integers."
            }

        peer_information = {
            "peer_id": peer_id,
            "host": host,
            "port": port,
            "pieces": sorted(set(pieces))
        }

        with registry_lock:
            if file_id not in peer_registry:
                peer_registry[file_id] = {}

            peer_registry[file_id][peer_id] = peer_information

        print(f"Registered peer {peer_id} for file {file_id}")

        return {
            "status": "success",
            "message": "Peer registered successfully."
        }

    def get_peers(self, request):
        """Finds other peers sharing the requested file."""

        file_id = request.get("file_id")
        requester_id = request.get("peer_id")

        if not file_id:
            return {
                "status": "error",
                "message": "file_id is required."
            }

        with registry_lock:
            available_peers = peer_registry.get(file_id, {})

            peers = [
                {
                    **information,
                    "pieces": list(information["pieces"])
                }
                for peer_id, information in available_peers.items()
                if peer_id != requester_id
            ]

        return {
            "status": "success",
            "peers": peers
        }

    def update_pieces(self, request):
        """Updates the pieces available at a registered peer."""

        peer_id = request.get("peer_id")
        file_id = request.get("file_id")
        pieces = request.get("pieces")

        if not peer_id or not file_id:
            return {
                "status": "error",
                "message": "peer_id and file_id are required."
            }

        if (
            not isinstance(pieces, list)
            or any(type(piece) is not int or piece < 0 for piece in pieces)
        ):
            return {
                "status": "error",
                "message": "pieces must contain non-negative integers."
            }

        with registry_lock:
            if file_id not in peer_registry:
                return {
                    "status": "error",
                    "message": "File is not registered."
                }

            if peer_id not in peer_registry[file_id]:
                return {
                    "status": "error",
                    "message": "Peer is not registered."
                }

            peer_registry[file_id][peer_id]["pieces"] = sorted(set(pieces))

        print(f"Updated pieces for peer {peer_id}: {sorted(set(pieces))}")

        return {
            "status": "success",
            "message": "Piece availability updated successfully."
        }

    def unregister_peer(self, request):
        """Removes a peer from the tracker."""

        peer_id = request.get("peer_id")
        file_id = request.get("file_id")

        if not peer_id or not file_id:
            return {
                "status": "error",
                "message": "peer_id and file_id are required."
            }

        with registry_lock:
            if file_id in peer_registry:
                peer_registry[file_id].pop(peer_id, None)

                if not peer_registry[file_id]:
                    del peer_registry[file_id]

        return {
            "status": "success",
            "message": "Peer unregistered successfully."
        }

    def get_stats(self):
        """Returns the number of tracked files and peers."""

        with registry_lock:
            files_tracked = len(peer_registry)

            registered_peers = sum(
                len(peers)
                for peers in peer_registry.values()
            )

        return {
            "status": "success",
            "files_tracked": files_tracked,
            "registered_peers": registered_peers
        }


class TrackerServer(socketserver.ThreadingTCPServer):
    """Allows multiple tracker requests to be handled concurrently."""

    allow_reuse_address = True
    daemon_threads = True


def main():
    with TrackerServer((HOST, PORT), TrackerHandler) as server:

        print("=" * 45)
        print("P2P FILE DISTRIBUTION - TRACKER")
        print("=" * 45)
        print(f"Tracker running at {HOST}:{PORT}")
        print("Waiting for peer requests...")
        print("Press Ctrl+C to stop the tracker.")

        try:
            server.serve_forever()

        except KeyboardInterrupt:
            print("\nStopping tracker...")


if __name__ == "__main__":
    main()
