import os
import tempfile

from peer.peer_server import PeerServer
from peer.file_manager import split_file, PIECE_SIZE

def main():
    print("=" * 45)
    print("PARTIAL PEER SERVER TEST")
    print("=" * 45)

    with tempfile.TemporaryDirectory() as temp_dir:
        file_path = os.path.join(temp_dir, "sample.txt")

        # Create a file containing three pieces
        with open(file_path, "wb") as file:
            file.write(b"A" * PIECE_SIZE)
            file.write(b"B" * PIECE_SIZE)
            file.write(b"C" * 100)

        all_pieces, _ = split_file(file_path)

        print(f"\nTotal pieces in file: {len(all_pieces)}")
        assert len(all_pieces) == 3

        # Create a peer that initially owns only piece 0
        peer = PeerServer(
            peer_id="partial_peer",
            file_id="test_file",
            file_path=file_path,
            initial_pieces=[0]
        )

        print("\n1. Checking initial pieces...")

        assert peer.available_pieces == {0}
        assert peer.pieces[0] is not None
        assert peer.pieces[1] is None
        assert peer.pieces[2] is None

        print("PASS: Peer initially owns only piece 0.")

        # Add another piece to the peer
        print("\n2. Adding another piece...")

        result = peer.add_piece(1, all_pieces[1])

        assert result is True
        assert peer.available_pieces == {0, 1}
        assert peer.pieces[1] == all_pieces[1]

        print("PASS: Peer successfully acquired piece 1.")

        # Check whether an invalid piece index is rejected
        print("\n3. Checking invalid piece index...")

        try:
            PeerServer(
                peer_id="invalid_peer",
                file_id="test_file",
                file_path=file_path,
                initial_pieces=[999]
            )
            raise AssertionError(
                "Invalid piece index should have been rejected."
            )
        except ValueError:
            print("PASS: Invalid piece index was rejected.")


        # Check whether incorrect piece data is rejected
        print("\n4. Checking piece verification...")

        try:
            peer.add_piece(2, b"incorrect data")
            raise AssertionError(
                "Incorrect piece data should have been rejected."
            )
        except ValueError:
            assert 2 not in peer.available_pieces
            print("PASS: Incorrect piece data was rejected.")

            print("\n" + "=" * 45)
            print("ALL PARTIAL PEER TESTS PASSED!")
            print("=" * 45)

if __name__ == "__main__":
    main()