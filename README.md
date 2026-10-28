# P2P File Distribution System

## 1. Overview

The P2P File Distribution System is a Python application inspired by BitTorrent-style peer-to-peer file sharing.
A central tracker helps peers discover other peers sharing a file. The actual file pieces are transferred directly between peers.

## 2. Objectives

- Implement a tracker for peer registration and discovery.
- Divide files into smaller pieces.
- Transfer pieces using TCP sockets.
- Verify piece integrity using SHA-256 hashes.
- Support sequential, random, and rarest-first piece-selection strategies.
- Support downloading pieces from multiple peers.
- Handle unavailable peers and missing pieces.
- Reconstruct the original file after downloading.

## 3. Technologies

- Python 3
- TCP socket programming
- Multithreading
- JSON
- SHA-256
- PowerShell for Windows commands

## 4. Main Components

### Tracker
Maintains information about shared files and registered peers. Supports registration, peer discovery, piece updates, peer removal, and statistics.

### Peer Server
Accepts incoming peer connections and provides requested file pieces.

### Peer Downloader
Discovers peers, requests pieces, verifies downloaded data, and reconstructs the output file.

### File Manager
Splits files into pieces, generates hashes, verifies pieces, and reconstructs files.

### Piece Manager
Selects the next piece to download according to the configured strategy.

### Peer Protocol
Defines the messages exchanged between peers, including handshake, bitfield, request, piece, have, and cancel messages.

### Tracker Client
Communicates with the tracker to register peers, discover other peers, update available pieces, and unregister.

## 5. File Integrity

The project uses pieces of 256 KiB, except when the final piece is smaller.
SHA-256 hashes are used to verify piece contents. This helps detect corrupted or modified data before it is accepted.

## 6. Installation

Install Python 3 and open PowerShell in the project directory.
No third-party Python packages are currently required by the implementation.

## 7. Running the Project

Open PowerShell in the project directory.

### Step 1: Start the tracker

Run the following command in the first terminal:   "python main.py tracker"

The tracker maintains information about registered peers and helps them discover other peers sharing the same file.
Keep this terminal running while testing the project.

### Step 2: Share a file

Open a second PowerShell terminal in the project directory and run:

"python main.py share --file ".\data\sample.txt" --peer-id peer_A --file-id sample_file"

This starts a peer server that shares the specified file.
The peer divides the file into pieces, makes the pieces available to other peers, and registers with the tracker.

### Step 3: Download the file

Open a third PowerShell terminal in the project directory and run:

"python main.py download --peer-id peer_B --file-id sample_file --metainfo ".\data\sample.txt.meta.json" --output ".\downloads\downloaded_sample.txt" --strategy sequential"

The downloader discovers available peers, requests the required pieces, verifies their integrity, and reconstructs the downloaded file.
The downloaded file is saved to the specified output path.
Available piece-selection strategies are:

* `sequential`: Requests missing pieces in ascending order.
* `random`: Selects missing pieces randomly.
* `rarest-first`: Prioritizes pieces reported as less common among the connected peers.

### Step 4: View tracker statistics

Run this command in another terminal:

"python main.py stats"

This displays tracker statistics, including the number of tracked files and registered peers.

### Step 5: View command help

To view the available commands:

"python main.py --help"

For help with individual commands:

"python main.py share --help"
"python main.py download --help"

## 8. Running the Tests

Run the tests from the project root directory.

For example:

python -m tests.test_file_manager
python -m tests.test_peer_protocol
python -m tests.test_peer_server
python -m tests.test_peer_downloader
python -m tests.test_tracker_integration
python -m tests.test_multi_peer_download
python -m tests.test_peer_failure
python -m tests.test_missing_piece
python -m tests.test_corrupted_piece


The project includes tests for tracker operations, file management, piece selection, peer communication, downloading, multi-peer transfers, unavailable peers, missing pieces, and corrupted pieces.
The full regression suite contains 14 test modules.

## 9. Limitations

* The current implementation is intended as an educational P2P file-distribution project.
* Peers use TCP sockets and localhost addresses for the demonstrated setup.
* The tracker helps peers discover one another, but file pieces are transferred directly between peers.
* The project is not a complete implementation of the BitTorrent protocol.
* Network accessibility, peer availability, and the presence of all required pieces affect whether a download succeeds.

## 10. Conclusion

The project demonstrates the main concepts behind peer-to-peer file distribution, including tracker-based peer discovery, file splitting, piece selection, TCP communication, multi-peer downloading, integrity verification, and file reconstruction.