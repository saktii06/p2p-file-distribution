import random


class PieceManager:
    """Keeps track of pieces and selects the next piece to download."""

    def __init__(self, total_pieces):
        self.total_pieces = total_pieces

        # Stores the indexes of pieces this peer already has
        self.have_pieces = set()

    def add_piece(self, piece_index):
        """Mark a piece as successfully received."""

        if 0 <= piece_index < self.total_pieces:
            self.have_pieces.add(piece_index)

    def get_missing_pieces(self):
        """Return the pieces that this peer does not have."""

        missing_pieces = []

        for piece_index in range(self.total_pieces):
            if piece_index not in self.have_pieces:
                missing_pieces.append(piece_index)

        return missing_pieces

    def select_piece(self, strategy, availability=None):
        """Choose the next missing piece using the selected strategy."""

        missing_pieces = self.get_missing_pieces()

        # No pieces remain to be downloaded
        if not missing_pieces:
            return None

        # Strategy 1: Sequential selection
        if strategy == "sequential":
            return missing_pieces[0]

        # Strategy 2: Random selection
        elif strategy == "random":
            return random.choice(missing_pieces)

        # Strategy 3: Rarest-first selection
        elif strategy == "rarest_first":

            if availability is None:
                raise ValueError(
                    "Availability information is required "
                    "for rarest-first selection."
                )

            # Start by assuming the first missing piece is the rarest
            rarest_piece = missing_pieces[0]
            lowest_availability = availability.get(
                rarest_piece, 0
            )

            # Find the missing piece with the lowest availability
            for piece_index in missing_pieces[1:]:

                piece_availability = availability.get(
                    piece_index, 0
                )

                if piece_availability < lowest_availability:
                    rarest_piece = piece_index
                    lowest_availability = piece_availability

            return rarest_piece

        else:
            raise ValueError("Unknown piece-selection strategy.")

    def is_complete(self):
        """Check whether this peer has every piece."""

        return len(self.have_pieces) == self.total_pieces