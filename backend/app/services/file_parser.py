from pathlib import Path


class FileParserService:
    def parse_text(self, file_path: str) -> str:
        path = Path(file_path)
        suffix = path.suffix.lower()
        if suffix == ".txt":
            return path.read_text(encoding="utf-8")
        if suffix == ".pdf":
            raise NotImplementedError("PDF parsing placeholder: connect pdf parser in a future iteration.")
        if suffix == ".docx":
            raise NotImplementedError("DOCX parsing placeholder: connect docx parser in a future iteration.")
        raise ValueError("Unsupported file type")
