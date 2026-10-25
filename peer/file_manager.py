import hashlib
import json
import os

# Size of each piece: 256 KB
PIECE_SIZE = 256 * 1024


def calculate_hash(data):
    """Calculate the SHA-256 hash of the given data."""

    return hashlib.sha256(data).hexdigest()


def split_file(file_path):
    """Divide a file into fixed-size pieces and calculate their hashes."""

    pieces = []
    piece_hashes = []

    # Open the original file in binary mode
    with open(file_path, "rb") as file:

        while True:
            # Read one piece
            piece = file.read(PIECE_SIZE)

            # Stop when the end of the file is reached
            if not piece:
                break

            # Store the piece and its hash
            pieces.append(piece)
            piece_hashes.append(calculate_hash(piece))

    return pieces, piece_hashes


def create_metainfo(file_path, piece_hashes):
    """Create metadata describing the file and its pieces."""

    file_size = os.path.getsize(file_path)

    metainfo = {
        "filename": os.path.basename(file_path),
        "file_size": file_size,
        "piece_size": PIECE_SIZE,
        "number_of_pieces": len(piece_hashes),
        "piece_hashes": piece_hashes
    }

    return metainfo


def save_metainfo(metainfo, output_path):
    """Save metainfo in JSON format."""

    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(metainfo, file, indent=4)


def verify_piece(piece, expected_hash):
    """Check whether a piece matches its expected hash."""

    actual_hash = calculate_hash(piece)

    return actual_hash == expected_hash


def reconstruct_file(pieces, output_path):
    """Combine pieces in order to recreate the original file."""

    with open(output_path, "wb") as file:

        for piece in pieces:
            file.write(piece)

    print(f"File reconstructed successfully: {output_path}")


def main():
    print("=" * 45)
    print("P2P FILE MANAGER")
    print("=" * 45)

    file_path = input("Enter the path of the file to share: ").strip()

    # Check whether the file exists
    if not os.path.isfile(file_path):
        print("Error: File does not exist.")
        return

    # Split the file and calculate piece hashes
    pieces, piece_hashes = split_file(file_path)

    print(f"\nOriginal file: {os.path.basename(file_path)}")
    print(f"File size: {os.path.getsize(file_path)} bytes")
    print(f"Piece size: {PIECE_SIZE} bytes")
    print(f"Number of pieces: {len(pieces)}")

    # Create and save metainfo
    metainfo = create_metainfo(file_path, piece_hashes)

    os.makedirs("data", exist_ok=True)

    metainfo_path = os.path.join(
        "data",
        os.path.basename(file_path) + ".meta.json"
    )

    save_metainfo(metainfo, metainfo_path)

    print(f"Metainfo saved to: {metainfo_path}")

    # Verify each piece
    all_valid = True

    for index, piece in enumerate(pieces):

        if verify_piece(piece, piece_hashes[index]):
            print(f"Piece {index}: Hash verified")
        else:
            print(f"Piece {index}: Hash verification failed")
            all_valid = False

    # Reconstruct the original file
    if all_valid:
        os.makedirs("downloads", exist_ok=True)

        reconstructed_path = os.path.join(
            "downloads",
            "reconstructed_" + os.path.basename(file_path)
        )

        reconstruct_file(pieces, reconstructed_path)

        print("\nAll pieces passed hash verification.")
        print("File management test completed.")


if __name__ == "__main__":
    main()