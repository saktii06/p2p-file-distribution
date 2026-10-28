import os
import tempfile

from peer.file_manager import split_file, verify_piece

def test_corrupted_piece():

    print("=" * 55)
    print("CORRUPTED PIECE TEST")
    print("=" * 55)

    # Step 1: Create a sample file
    print("\n1. Creating sample file...")

    original_data = b"P2P file distribution testing data! " * 20000

    with tempfile.TemporaryDirectory() as temp_dir:
        original_path = os.path.join(temp_dir, "original.txt")

        with open(original_path, "wb") as file:
            file.write(original_data)

        print("Original file size:", len(original_data))

        # Step 2: Split the file into pieces
        print("\n2. Splitting file into pieces...")

        pieces, piece_hashes = split_file(original_path)

        print("Number of pieces:", len(pieces))

        assert len(pieces) > 0, "No pieces were generated."
        assert len(pieces) == len(piece_hashes), (
            "Piece and hash counts do not match."
        )

        print("PASS: File split successfully.")

        # Step 3: Verify all original pieces
        print("\n3. Verifying original pieces...")

        for index, piece in enumerate(pieces):
            assert verify_piece(piece, piece_hashes[index]), (
                f"Original piece {index} failed verification."
            )
            print(f"Piece {index}: Hash verification passed.")

        print("PASS: All original pieces are valid.")

        # Step 4: Modify one byte in the first piece
        print("\n4. Corrupting piece 0...")

        original_piece = pieces[0]

        corrupted_piece = (
            bytes([original_piece[0] ^ 1]) + original_piece[1:]
        )

        assert corrupted_piece != original_piece

        print("PASS: Piece contents modified.")

        # Step 5: Verify the corrupted piece
        print("\n5. Checking corrupted piece...")

        result = verify_piece(corrupted_piece, piece_hashes[0])

        assert result is False, (
            "ERROR: Corrupted piece was incorrectly accepted."
        )

        print("PASS: Corrupted piece was rejected.")

    print("\n" + "=" * 55)
    print("ALL CORRUPTED PIECE TESTS PASSED!")
    print("=" * 55)

if __name__ == "__main__":
    test_corrupted_piece()
