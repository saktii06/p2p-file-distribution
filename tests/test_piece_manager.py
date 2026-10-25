import os
import sys

# Allow Python to find the peer package
project_folder = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

sys.path.insert(0, project_folder)

from peer.piece_manager import PieceManager


def main():
    print("=" * 45)
    print("PIECE MANAGER TESTS")
    print("=" * 45)

    # Create a peer that needs 6 pieces
    manager = PieceManager(6)

    # Assume the peer already has Pieces 0 and 2
    manager.add_piece(0)
    manager.add_piece(2)

    print("\n1. Testing missing pieces...")

    missing = manager.get_missing_pieces()

    print("Missing pieces:", missing)

    assert missing == [1, 3, 4, 5]

    print("PASS: Missing pieces identified correctly.")

    print("\n2. Testing sequential selection...")

    piece = manager.select_piece("sequential")

    print("Selected piece:", piece)

    assert piece == 1

    print("PASS: Sequential selection works.")

    print("\n3. Testing random selection...")

    piece = manager.select_piece("random")

    print("Selected piece:", piece)

    assert piece in [1, 3, 4, 5]

    print("PASS: Random selection chooses a missing piece.")

    print("\n4. Testing rarest-first selection...")

    availability = {
        0: 5,
        1: 3,
        2: 4,
        3: 1,
        4: 2,
        5: 4
    }

    piece = manager.select_piece(
        "rarest_first",
        availability
    )

    print("Selected piece:", piece)

    assert piece == 3

    print("PASS: Rarest-first selects the rarest missing piece.")

    print("\n5. Testing piece completion...")

    for piece_index in range(6):
        manager.add_piece(piece_index)

    assert manager.is_complete()

    print("PASS: Completion detected correctly.")

    print("\n6. Testing no missing pieces...")

    assert manager.select_piece("sequential") is None

    print("PASS: No piece selected when download is complete.")

    print("\n" + "=" * 45)
    print("ALL PIECE MANAGER TESTS PASSED!")
    print("=" * 45)


if __name__ == "__main__":
    main()