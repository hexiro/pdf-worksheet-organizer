class PdfWorksheetOrganizerException(Exception):
    """Base class for exceptions in this module."""
    pass

class NoAvailablePositionException(PdfWorksheetOrganizerException):
    """Raised when no available position can be found for an element."""
    
    def __init__(self, element_name: str) -> None:
        super().__init__(f"No available position for {element_name}")