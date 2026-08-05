from pypdf import PdfReader


def extract_text_from_pdf(pdf_path: str) -> str:
    """读取 PDF，并返回其中的全部文本。"""
    reader = PdfReader(pdf_path)
    pages_text = []

    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            pages_text.append(page_text)

    return "\n".join(pages_text)


if __name__ == "__main__":
    text = extract_text_from_pdf("data/resume.pdf")
    print(text)
