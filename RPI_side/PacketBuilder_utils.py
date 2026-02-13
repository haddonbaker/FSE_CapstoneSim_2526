def chType_from_logical_id(logical_id: str) -> str:
    """
    Determines chType (ai, ao, di, do) from logical_id string.
    SPI1 = inputs (ai, di)
    SPI2 = outputs (ao, do)
    Returns 'ai' or 'di' for SPI1, 'ao' or 'do' for SPI2, based on further context if available.
    """
    if logical_id is None:
        return None
    # Infer slot number from logical_id
    import re
    match = re.match(r"SPI\d+_CARD(\d+)_SLOT(\d+)", logical_id)
    if not match:
        return None
    card_num = int(match.group(1)) - 1
    slot_num = int(match.group(2))
    absolute_slot = card_num * 8 + slot_num
    if 0 <= absolute_slot <= 31:
        return "ao"
    elif 32 <= absolute_slot <= 39:
        return "ai"
    elif 40 <= absolute_slot <= 55:
        return "do"
    elif 56 <= absolute_slot <= 71:
        return "di"
    else:
        return None

def slot_from_logical_id(logical_id: str) -> int:
    """
    Determines slot number from logical_id string.
    """
    if logical_id is None:
        return None
    # Infer slot number from logical_id
    import re
    match = re.match(r"SPI\d+_CARD(\d+)_SLOT(\d+)", logical_id)
    if not match:
        return None
   
    slot_num = int(match.group(2))
    return slot_num
   
def spi_from_logical_id(logical_id: str) -> int:
    """
    Determines SPI number from logical_id string.
    """
    if logical_id is None:
        return None
    # Infer SPI number from logical_id
    import re
    match = re.match(r"SPI(\d+)_CARD(\d+)_SLOT(\d+)", logical_id)
    if not match:
        return None
   
    spi_num = int(match.group(1))
    return spi_num

def card_pos_from_logical_id(logical_id: str) -> int:
    """
    Returns the absolute card position (card_num) from a logical_id string of the form SPIx_CARDx_SLOTx.
    Returns a 0-based index (e.g. CARD1 -> 0).
    Example: SPI1_CARD3_SLOT2 -> returns 2
    """
    if logical_id is None:
        return None
    import re
    match = re.match(r"SPI\d+_CARD(\d+)_SLOT(\d+)", logical_id)
    if not match:
        return None
    card_num = int(match.group(1)) - 1
    return card_num
