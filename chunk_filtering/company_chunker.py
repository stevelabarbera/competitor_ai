from company_metadata.tagging import chunk_text_with_company_context

class CompanyChunker:
    def __init__(self, file_name, file_content, chunk_size=512, overlap=64):
        self.file_name = file_name
        self.file_content = file_content
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self):
        return chunk_text_with_company_context(
            self.file_content,
            self.file_name,
            chunk_size=self.chunk_size,
            overlap=self.overlap
        )
