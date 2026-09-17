import fitz

from app.services.parser import parse_document


def _create_pdf(text: str | None = None) -> bytes:
	document = fitz.open()
	page = document.new_page()
	if text is not None:
		page.insert_text((72, 72), text)
	pdf_bytes = document.tobytes()
	document.close()
	return pdf_bytes


def test_parse_valid_txt() -> None:
	result = parse_document(
		b"Jane Doe\nPython developer with FastAPI experience.",
		"resume.txt",
	)

	assert result.success is True
	assert "Python developer" in result.text
	assert result.file_type == "txt"


def test_parse_valid_pdf() -> None:
	pdf_bytes = _create_pdf(
		"Jane Doe - Python Engineer with experience building reliable APIs"
	)

	result = parse_document(pdf_bytes, "resume.pdf")

	assert result.success is True
	assert "Python Engineer" in result.text
	assert result.file_type == "pdf"


def test_parse_image_only_pdf_as_unreadable() -> None:
	result = parse_document(_create_pdf(), "scanned_resume.pdf")

	assert result.success is False
	assert result.text == ""
	assert result.error == "Unable to extract sufficient text from the PDF."


def test_parse_unsupported_file_type() -> None:
	result = parse_document(b"resume content", "resume.docx")

	assert result.success is False
	assert result.text == ""
	assert "Unsupported file type" in (result.error or "")


def test_parse_empty_txt() -> None:
	result = parse_document(b" \n\t", "empty.txt")

	assert result.success is False
	assert result.text == ""
	assert result.error == "The TXT file is empty."


def test_parse_invalid_txt_encoding() -> None:
	result = parse_document(b"\xff\xfe\xfd", "invalid.txt")

	assert result.success is False
	assert result.text == ""
	assert result.error == "Unable to decode the TXT file as UTF-8."


def test_parse_invalid_pdf_bytes_without_raising() -> None:
	result = parse_document(b"not a PDF", "invalid.pdf")

	assert result.success is False
	assert result.text == ""
	assert result.error == "Unable to read the PDF document."
