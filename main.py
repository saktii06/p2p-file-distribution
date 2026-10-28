import argparse
import os
import sys
import threading

from tracker.tracker import main as start_tracker
from peer.peer_server import PeerServer
from peer.peer_downloader import PeerDownloader
from peer.file_manager import split_file, create_metainfo, save_metainfo
from peer.tracker_client import TrackerClient


def share_file(args):
    """Start a peer server and share a file."""

    file_path = os.path.abspath(args.file)

    if not os.path.isfile(file_path):
        print("Error: The specified file does not exist.")
        return

    file_name = os.path.basename(file_path)

    # Generate metainfo for the file.
    pieces, piece_hashes = split_file(file_path)

    metainfo = create_metainfo(file_path, piece_hashes)

    os.makedirs("data", exist_ok=True)

    metainfo_path = os.path.join(
        "data",
        file_name + ".meta.json"
    )

    save_metainfo(metainfo, metainfo_path)

    print("\nFile information")
    print("-" * 40)
    print(f"Filename: {file_name}")
    print(f"File size: {os.path.getsize(file_path)} bytes")
    print(f"Number of pieces: {len(pieces)}")
    print(f"Metainfo saved to: {metainfo_path}")

    # Start the peer server.
    server = PeerServer(
        peer_id=args.peer_id,
        file_id=args.file_id,
        file_path=file_path,
        host=args.host,
        port=args.port,
        use_tracker=True
    )

    try:
        server.start()

        print("\nFile sharing started successfully.")
        print(f"Peer ID: {args.peer_id}")
        print(f"File ID: {args.file_id}")
        print(f"Address: {args.host}:{server.port}")
        print("Press Ctrl+C to stop sharing.")

        while True:
            threading.Event().wait(1)

    except KeyboardInterrupt:
        print("\nStopping file sharing...")

    except (OSError, ValueError, RuntimeError) as error:
        print(f"Error: {error}")

    finally:
        server.stop()


def download_file(args):
    """Download a file from peers registered with the tracker."""

    metainfo_path = os.path.abspath(args.metainfo)
    output_path = os.path.abspath(args.output)

    if not os.path.isfile(metainfo_path):
        print("Error: Metainfo file does not exist.")
        return

    downloader = PeerDownloader(
        peer_id=args.peer_id,
        file_id=args.file_id,
        metainfo_path=metainfo_path,
        output_path=output_path,
        strategy=args.strategy,
        tracker_host=args.host,
        tracker_port=args.tracker_port
    )

    success = downloader.download()

    if not success:
        sys.exit(1)


def show_stats(args):
    """Display tracker statistics."""

    try:
        client = TrackerClient(
            tracker_host=args.host,
            tracker_port=args.port
        )

        stats = client.get_stats()

        print("\nTracker Statistics")
        print("-" * 30)
        print(f"Files tracked: {stats['files_tracked']}")
        print(f"Registered peers: {stats['registered_peers']}")

    except (OSError, ConnectionError, RuntimeError, ValueError) as error:
        print(f"Could not retrieve tracker statistics: {error}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="P2P File Distribution System"
    )

    commands = parser.add_subparsers(
        dest="command",
        required=True
    )

    # Tracker command.
    commands.add_parser(
        "tracker",
        help="Start the tracker server"
    )

    # Share command.
    share_parser = commands.add_parser(
        "share",
        help="Share a file with other peers"
    )

    share_parser.add_argument(
        "--file",
        required=True,
        help="Path of the file to share"
    )

    share_parser.add_argument(
        "--peer-id",
        required=True,
        help="Unique ID for this peer"
    )

    share_parser.add_argument(
        "--file-id",
        required=True,
        help="ID used by peers to identify the shared file"
    )

    share_parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="IP address used by this peer"
    )

    share_parser.add_argument(
        "--port",
        type=int,
        default=0,
        help="Peer port; 0 selects an available port"
    )

    # Download command.
    download_parser = commands.add_parser(
        "download",
        help="Download a file from other peers"
    )

    download_parser.add_argument(
        "--peer-id",
        required=True,
        help="Unique ID for the downloading peer"
    )

    download_parser.add_argument(
        "--file-id",
        required=True,
        help="ID of the file to download"
    )

    download_parser.add_argument(
        "--metainfo",
        required=True,
        help="Path of the file's metainfo JSON"
    )

    download_parser.add_argument(
        "--output",
        required=True,
        help="Path where the downloaded file will be saved"
    )

    download_parser.add_argument(
        "--strategy",
        choices=["sequential", "random", "rarest-first"],
        default="sequential",
        help="Piece-selection strategy"
    )

    download_parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Tracker IP address"
    )

    download_parser.add_argument(
        "--tracker-port",
        type=int,
        default=5000,
        help="Tracker port"
    )

    # Statistics command.
    stats_parser = commands.add_parser(
        "stats",
        help="Display tracker statistics"
    )

    stats_parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Tracker IP address"
    )

    stats_parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Tracker port"
    )

    args = parser.parse_args()

    if args.command == "tracker":
        start_tracker()

    elif args.command == "share":
        share_file(args)

    elif args.command == "download":
        download_file(args)

    elif args.command == "stats":
        show_stats(args)


if __name__ == "__main__":
    main()