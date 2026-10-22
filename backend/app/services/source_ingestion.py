import re
from typing import List, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.project import SourceDocument, SourceSection
from backend.app.services.storage import storage_service
from backend.app.core.security import sanitize_untrusted_text

class SourceIngestionService:
    @staticmethod
    def parse_sections(raw_text: str) -> List[Dict[str, Any]]:
        """
        Splits manuscript text into logical chapters/sections based on markdown headings 
        or common patterns like 'Chapter X', 'Act Y', 'Scene Z'.
        """
        lines = raw_text.splitlines(keepends=True)
        sections = []
        current_title = "Prologue / Introduction"
        current_content_lines = []
        start_char = 0
        current_char = 0
        
        chapter_regex = re.compile(r"^(#{1,3}\s+|chapter\s+\d+|act\s+\d+|scene\s+\d+|part\s+\d+)", re.IGNORECASE)

        for line in lines:
            line_len = len(line)
            stripped = line.strip()
            if chapter_regex.match(stripped) and current_content_lines:
                # Flush previous section
                content_str = "".join(current_content_lines).strip()
                if content_str:
                    sections.append({
                        "title": current_title,
                        "content": content_str,
                        "start_char": start_char,
                        "end_char": current_char
                    })
                current_title = stripped.lstrip("#").strip()
                current_content_lines = []
                start_char = current_char

            current_content_lines.append(line)
            current_char += line_len

        # Flush final section
        content_str = "".join(current_content_lines).strip()
        if content_str:
            sections.append({
                "title": current_title,
                "content": content_str,
                "start_char": start_char,
                "end_char": current_char
            })

        if not sections:
            sections.append({
                "title": "Complete Manuscript",
                "content": raw_text.strip(),
                "start_char": 0,
                "end_char": len(raw_text)
            })

        return sections

    @classmethod
    async def ingest_document(
        cls,
        db: AsyncSession,
        project_id: str,
        filename: str,
        raw_bytes: bytes,
        mime_type: str = "text/plain"
    ) -> SourceDocument:
        # Save raw manuscript securely
        storage_key, checksum, file_size = storage_service.save_bytes("documents", filename, raw_bytes)
        
        raw_text = raw_bytes.decode("utf-8", errors="replace")
        sanitized_text = sanitize_untrusted_text(raw_text)
        
        words = len(sanitized_text.split())
        chars = len(sanitized_text)

        doc = SourceDocument(
            project_id=project_id,
            filename=filename,
            storage_key=storage_key,
            checksum=checksum,
            mime_type=mime_type,
            char_count=chars,
            word_count=words,
            extraction_status="extracted",
            metadata_info={"original_size_bytes": file_size}
        )
        db.add(doc)
        await db.flush()

        parsed_sections = cls.parse_sections(sanitized_text)
        for idx, sec in enumerate(parsed_sections):
            section_obj = SourceSection(
                document_id=doc.id,
                section_index=idx + 1,
                title=sec["title"],
                content=sec["content"],
                start_char=sec["start_char"],
                end_char=sec["end_char"]
            )
            db.add(section_obj)

        await db.commit()
        await db.refresh(doc)
        return doc

source_ingestion_service = SourceIngestionService()
