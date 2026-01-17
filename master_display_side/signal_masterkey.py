# Created by Haddon Baker 1/17/26 with assistance from ChatGPT

import customtkinter as ctk


def infer_spi_bus(sig_type: str) -> int:
        st = sig_type.strip().lower()

        # Inputs → SPI 1, Outputs → SPI 2
        if st.endswith("i"):     # ai, di
            return 1
        elif st.endswith("o"):   # ao, do
            return 2
        else:
            raise ValueError(f"Unknown sig_type: {sig_type}")
        

    
def infer_card_type(sig_type: str) -> str:
    if not sig_type:
        raise ValueError("sig_type is empty")

    return sig_type.strip().upper()


def get_card_type_name(signals: list) -> str:
    """Determine card type name from its signals."""
    if not signals:
        return "Mixed"
    
    # Get the signal type from the first signal
    sig_type = signals[0].sig_type.lower()
    
    if sig_type.startswith("a"):
        if sig_type.endswith("i"):
            return "Analog Inputs"
        elif sig_type.endswith("o"):
            return "Analog Outputs"
    elif sig_type.startswith("d"):
        if sig_type.endswith("i"):
            return "Digital Inputs"
        elif sig_type.endswith("o"):
            return "Digital Outputs"
    
    return "Mixed"


class SignalMasterKey(ctk.CTkFrame):
    """Displays signal configuration organized by card in a scrollable view."""
    SLOTS_PER_CARD = 8
    CARDS_PER_ROW = 3
    
    def __init__(self, parent, signals: list[dict]):
        super().__init__(parent)

        self.title = ctk.CTkLabel(
            self,
            text="Signal Configuration",
            font=ctk.CTkFont(size=22, weight="bold")
        )
        self.title.pack(pady=10)

        # Create scrollable frame
        self.scrollable_frame = ctk.CTkScrollableFrame(self, corner_radius=10)
        self.scrollable_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Configure grid for card layout with equal spacing - 3 columns
        self.scrollable_frame.grid_columnconfigure((0, 1, 2), weight=1)
        self.scrollable_frame.grid_rowconfigure(tuple(range(10)), weight=1)

        # Parse signals
        self.signal_configs = [
            SignalConfiguration(i, sig)
            for i, sig in enumerate(signals)
        ]

        # Group by card
        self._populate_by_card()

    def _populate_by_card(self):
        """Organize signals by card and display in a grid."""
        cards = {}
        
        # Group signals by card number
        for sig in self.signal_configs:
            card_num = sig.card_number
            if card_num not in cards:
                cards[card_num] = []
            cards[card_num].append(sig)
        
        # Display cards in grid
        row = 0
        col = 0
        
        for card_num in sorted(cards.keys()):
            card_signals = cards[card_num]
            
                        # Create card table frame with larger size
            card_frame = ctk.CTkFrame(self.scrollable_frame, corner_radius=10, fg_color="#2a2a2a")
            card_frame.grid(row=row, column=col, padx=15, pady=15, sticky="nsew")
            card_frame.grid_propagate(False)
            
            # Set minimum height for cards
            card_frame.configure(height=400)
            
            # Card title with type name
            card_type_name = get_card_type_name(card_signals)
            card_title = ctk.CTkLabel(
                card_frame,
                text=f"Card {card_num}: {card_type_name}",
                font=ctk.CTkFont(size=16, weight="bold"),
                text_color="#7CB9E8"
            )
            card_title.pack(pady=(15, 10), padx=15)
            
            # Card table with larger fonts
            table_frame = ctk.CTkFrame(card_frame, fg_color="transparent")
            table_frame.pack(padx=15, pady=(0, 15), fill="both", expand=True)
            
            headers = ["Name", "Card Slot", "Board Slot", "SPI Bus"]
            
            # Configure columns for centering
            for col_idx in range(len(headers)):
                table_frame.grid_columnconfigure(col_idx, weight=1)
            
            # Headers
            for col_idx, header in enumerate(headers):
                ctk.CTkLabel(
                    table_frame,
                    text=header,
                    font=ctk.CTkFont(weight="bold", size=12),
                    text_color="#B8A569"
                ).grid(row=0, column=col_idx, padx=6, pady=8, sticky="ew")
            
            # Signal rows with larger fonts
            for row_idx, sig in enumerate(sorted(card_signals, key=lambda s: s.card_slot), start=1):
                values = [
                    sig.name,
                    sig.card_slot,
                    sig.board_slot,
                    sig.spi_bus
                ]
                
                for col_idx, value in enumerate(values):
                    ctk.CTkLabel(
                        table_frame,
                        text=str(value),
                        font=ctk.CTkFont(size=13)
                    ).grid(row=row_idx, column=col_idx, padx=6, pady=6, sticky="ew")
            
            # Move to next position
            col += 1
            if col >= self.CARDS_PER_ROW:
                col = 0
                row += 1
        
        # Center last card(s) if odd number
        num_cards = len(cards)
        remainder = num_cards % self.CARDS_PER_ROW
        
        if remainder != 0:
            # Get the last row cards
            last_row_cards = list(self.scrollable_frame.grid_slaves(row=row, column=0))
            
            # Calculate columnspan to center them
            if remainder == 1:
                columnspan = 3
                center_col = 1
            elif remainder == 2:
                columnspan = 1
                center_col = 0
            else:
                columnspan = 1
                center_col = 0
            
            # Re-grid the last row cards to center them
            if remainder == 1:
                for card in last_row_cards:
                    card.grid(row=row, column=1, padx=15, pady=15, sticky="nsew")

class SignalConfiguration:
    SLOTS_PER_CARD = 8

    def __init__(self, signal_index: int, signal_data: dict):
        self.index = signal_index
        self.name = signal_data["name"]

        raw_type = signal_data["sig_type"]
        self.sig_type = raw_type.strip().lower()

        self.board_slot = signal_data["boardSlotPosition"]

        self.card_number = (signal_index // self.SLOTS_PER_CARD) + 1
        self.card_slot = signal_index % self.SLOTS_PER_CARD
        self.card_type = infer_card_type(raw_type)
        self.spi_bus = infer_spi_bus(raw_type)

    def as_dict(self):
        return {
            "index": self.index,
            "name": self.name,
            "sig_type": self.sig_type,
            "board_slot": self.board_slot,
            "card_number": self.card_number,
            "card_slot": self.card_slot,
            "card_type": self.card_type,
            "spi_bus": self.spi_bus
        }