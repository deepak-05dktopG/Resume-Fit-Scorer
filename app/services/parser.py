from pathlib import Path

import fitz
from pydantic import BaseModel


MIN_PDF_TEXT_CHARACTERS = 50


class ParseResult(BaseModel):
	"""Structured result returned by the document parser."""

	success: bool
	text: str
	filename: str
	file_type: str
	error: str | None = None


def parse_document(file_content: bytes, filename: str) -> ParseResult:
	"""Extract text from a supported PDF or TXT document."""

	file_type = Path(filename).suffix.lower().lstrip(".")

	if file_type == "txt":
		return _parse_text(file_content, filename)
	if file_type == "pdf":
		return _parse_pdf(file_content, filename)

	return ParseResult(
		success=False,
		text="",
		filename=filename,
		file_type=file_type or "unknown",
		error="Unsupported file type. Only .pdf and .txt files are supported.",
	)


def _parse_text(file_content: bytes, filename: str) -> ParseResult:
	try:
		text = file_content.decode("utf-8-sig")
	except UnicodeDecodeError:
		return ParseResult(
			success=False,
			text="",
			filename=filename,
			file_type="txt",
			error="Unable to decode the TXT file as UTF-8.",
		)

	normalized_text = _normalize_text(text)
	if not normalized_text:
		return ParseResult(
			success=False,
			text="",
			filename=filename,
			file_type="txt",
			error="The TXT file is empty.",
		)

	return ParseResult(
		success=True,
		text=normalized_text,
		filename=filename,
		file_type="txt",
	)


def _parse_pdf(file_content: bytes, filename: str) -> ParseResult:
	try:
		with fitz.open(stream=file_content, filetype="pdf") as document:
			page_text = [page.get_text() for page in document]
	except (fitz.FileDataError, RuntimeError, ValueError):
		return ParseResult(
			success=False,
			text="",
			filename=filename,
			file_type="pdf",
			error="Unable to read the PDF document.",
		)

	normalized_text = _normalize_text("\n\n".join(page_text))
	character_count = len("".join(normalized_text.split()))
	if character_count < MIN_PDF_TEXT_CHARACTERS:
		return ParseResult(
			success=False,
			text="",
			filename=filename,
			file_type="pdf",
			error="Unable to extract sufficient text from the PDF.",
		)

	return ParseResult(
		success=True,
		text=normalized_text,
		filename=filename,
		file_type="pdf",
	)


def _normalize_text(text: str) -> str:
	lines = [" ".join(line.split()) for line in text.splitlines()]
	normalized_lines: list[str] = []
	blank_line_added = False

	for line in lines:
		if line:
			normalized_lines.append(line)
			blank_line_added = False
		elif normalized_lines and not blank_line_added:
			normalized_lines.append("")
			blank_line_added = True

	return "\n".join(normalized_lines).strip()
