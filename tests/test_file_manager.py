import os
import sys
import tempfile
import json

# Allow Python to find the peer package
project_folder = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

sys.path.insert(0, project_folder)

from peer.file_manager import (
    split_file,
    verify_piece,
    reconstruct_file,
    create_metainfo,
    save_metainfo
)


def main():
    print("=" * 45)
    print("FILE MANAGER TESTS")
    print("=" * 45)

    # Create a temporary folder for testing
    with tempfile.TemporaryDirectory() as folder:

        original_path = os.path.join(folder, "original.txt")

        # Create a file larger than 256 KB
        original_data = (
            b"This is a P2P file distribution test.\n" * 20000
        )

        with open(original_path, "wb") as file:
            file.write(original_data)

        print("\n1. Testing file splitting...")

        pieces, piece_hashes = split_file(original_path)

        print("Number of pieces:", len(pieces))

        assert len(pieces) > 1
        print("PASS: File divided into multiple pieces.")

        print("\n2. Testing piece verification...")

        for index, piece in enumerate(pieces):
            assert verify_piece(piece, piece_hashes[index])

        print("PASS: All original pieces passed verification.")

        print("\n3. Testing modified piece...")

        modified_piece = pieces[0] + b"modified"

        assert not verify_piece(
            modified_piece,
            piece_hashes[0]
        )

        print("PASS: Modified piece was rejected.")

        print("\n4. Testing metainfo generation...")

        metainfo = create_metainfo(
            original_path,
            piece_hashes
        )

        metainfo_path = os.path.join(
            folder,
            "original.txt.meta.json"
        )

        save_metainfo(metainfo, metainfo_path)

        with open(metainfo_path, "r", encoding="utf-8") as file:
            loaded_metainfo = json.load(file)

        assert loaded_metainfo["filename"] == "original.txt"
        assert loaded_metainfo["file_size"] == len(original_data)
        assert loaded_metainfo["number_of_pieces"] == len(pieces)

        print("PASS: Metainfo saved and loaded correctly.")

        print("\n5. Testing file reconstruction...")

        reconstructed_path = os.path.join(
            folder,
            "reconstructed.txt"
        )

        reconstruct_file(pieces, reconstructed_path)

        with open(reconstructed_path, "rb") as file:
            reconstructed_data = file.read()

        assert reconstructed_data == original_data

        print("PASS: Reconstructed file matches the original.")

    print("\n" + "=" * 45)
    print("ALL FILE MANAGER TESTS PASSED!")
    print("=" * 45)


if __name__ == "__main__":
    main()