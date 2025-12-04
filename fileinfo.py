from dataclasses import dataclass
@dataclass
class FileInfo:
    sector_start: int
    block_size: int
    filename: str
    offset: int
    data_banks: list = None
    memory: memoryview = None

