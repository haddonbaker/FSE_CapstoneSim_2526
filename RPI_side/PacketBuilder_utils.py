def chType_from_logical_id(logical_id: str) -> str:
    """
    Determines chType (ai, ao, di, do) from logical_id string.
    SPI1 = inputs (ai, di)
    SPI2 = outputs (ao, do)
    
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

    print("*"*100)
    print(f"logical id is: {logical_id} and absolute slot is:{absolute_slot}")
    print("*"*100)
    if 1 <= absolute_slot <= 32:
        return "ao"
    elif 33 <= absolute_slot <= 48:
        return "do"
    elif 49 <= absolute_slot <= 56:
        return "ai"
    elif 57 <= absolute_slot <= 72:
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
    Example: SPI1_CARD3_SLOT2 -> returns 3
    """
    if logical_id is None:
        return None
    import re
    match = re.match(r"SPI\d+_CARD(\d+)_SLOT(\d+)", logical_id)
    if not match:
        return None
    card_num = int(match.group(1))
    return card_num
