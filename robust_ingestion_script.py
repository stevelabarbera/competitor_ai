#!/usr/bin/env python3
"""
Robust Document Ingestion Script
================================
This script handles document ingestion with proper error handling,
encoding detection, and metadata validation.
"""

import os
import sys
import traceback
from pathlib import Path
import chardet
import chromadb
from typing import List, Dict, Optional, Tuple
import hashlib
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ingestion.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class DocumentIngester:
    """Handles document ingestion with robust error handling"""
    
    def __init__(self, chroma_path: str = "./chroma_db"):
        self.chroma_path = chroma_path
        self.client = None
        self.collection = None
        self.batch_size = 100
        self.current_batch = {
            'documents': [],
            'metadatas': [],
            'ids': []
        }
        
    def initialize_chroma(self, collection_name: str = "competitor_docs"):
        """Initialize ChromaDB client and collection"""
        try:
            logger.info(f"Initializing ChromaDB at {self.chroma_path}")
            self.client = chromadb.PersistentClient(path=self.chroma_path)
            
            # Try to get existing collection or create new one
            try:
                self.collection = self.client.get_collection(name=collection_name)
                logger.info(f"Using existing collection: {collection_name}")
            except:
                self.collection = self.client.create_collection(
                    name=collection_name,
                    metadata={"hnsw:space": "cosine"}
                )
                logger.info(f"Created new collection: {collection_name}")
                
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            return False
    
    def detect_encoding(self, file_path: str) -> Optional[str]:
        """Detect file encoding using chardet"""
        try:
            with open(file_path, 'rb') as f:
                raw_data = f.read()
            
            result = chardet.detect(raw_data)
            confidence = result.get('confidence', 0)
            encoding = result.get('encoding')
            
            if confidence > 0.7 and encoding:
                logger.debug(f"Detected encoding {encoding} with confidence {confidence:.2f}")
                return encoding
            else:
                logger.warning(f"Low confidence encoding detection: {encoding} ({confidence:.2f})")
                return None
                
        except Exception as e:
            logger.error(f"Error detecting encoding for {file_path}: {e}")
            return None
    
    def read_file_with_encoding(self, file_path: str) -> Optional[str]:
        """Read file with multiple encoding attempts"""
        
        # Try detected encoding first
        detected_encoding = self.detect_encoding(file_path)
        encodings_to_try = []
        
        if detected_encoding:
            encodings_to_try.append(detected_encoding)
        
        # Add common encodings
        encodings_to_try.extend([
            'utf-8', 'utf-8-sig', 'latin-1', 'cp1252', 
            'ascii', 'iso-8859-1', 'windows-1252'
        ])
        
        # Remove duplicates while preserving order
        seen = set()
        encodings_to_try = [x for x in encodings_to_try if not (x in seen or seen.add(x))]
        
        for encoding in encodings_to_try:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                logger.debug(f"Successfully read {file_path} with encoding: {encoding}")
                return content
                
            except (UnicodeDecodeError, UnicodeError) as e:
                logger.debug(f"Failed to read {file_path} with {encoding}: {e}")
                continue
            except Exception as e:
                logger.error(f"Unexpected error reading {file_path} with {encoding}: {e}")
                continue
        
        # If all encodings fail, try binary mode and ignore errors
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            logger.warning(f"Read {file_path} with error ignoring - some characters may be lost")
            return content
        except Exception as e:
            logger.error(f"Could not read file {file_path} with any encoding method: {e}")
            return None
    
    def generate_chunk_id(self, content: str, metadata: Dict) -> str:
        """Generate unique ID for chunk"""
        # Create a hash based on content and source
        content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()[:8]
        source = metadata.get('source', 'unknown')
        return f"{Path(source).stem}_{content_hash}"
    
    def validate_chunk(self, content: str, metadata: Dict) -> bool:
        """Validate chunk before adding to collection"""
        
        # Check content is not empty and has minimum length
        if not content or len(content.strip()) < 10:
            logger.warning("Chunk content too short or empty")
            return False
        
        # Check metadata is not None and has required fields
        if metadata is None:
            logger.warning("Chunk metadata is None")
            return False
        
        if not isinstance(metadata, dict):
            logger.warning("Chunk metadata is not a dictionary")
            return False
        
        # Check required fields
        required_fields = ['source']
        for field in required_fields:
            if field not in metadata:
                logger.warning(f"Missing required metadata field: {field}")
                return False
        
        # Check source is not empty
        if not metadata['source'] or not metadata['source'].strip():
            logger.warning("Source field is empty")
            return False
        
        return True
    
    def chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """Simple text chunking with overlap"""
        if not text:
            return []
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            
            # Try to break at sentence boundary
            if end < len(text):
                last_period = chunk.rfind('.')
                last_newline = chunk.rfind('\n')
                break_point = max(last_period, last_newline)
                
                if break_point > start + chunk_size // 2:
                    chunk = text[start:break_point + 1]
                    end = break_point + 1
            
            chunks.append(chunk.strip())
            start = end - overlap
            
            if start >= len(text):
                break
        
        return [chunk for chunk in chunks if chunk.strip()]
    
    def add_to_batch(self, content: str, metadata: Dict):
        """Add document to current batch"""
        
        # Validate chunk
        if not self.validate_chunk(content, metadata):
            logger.warning("Skipping invalid chunk")
            return False
        
        # Generate unique ID
        chunk_id = self.generate_chunk_id(content, metadata)
        
        # Add to batch
        self.current_batch['documents'].append(content)
        self.current_batch['metadatas'].append(metadata)
        self.current_batch['ids'].append(chunk_id)
        
        logger.debug(f"Added chunk to batch: {chunk_id}")
        
        # Flush batch if full
        if len(self.current_batch['documents']) >= self.batch_size:
            return self.flush_batch()
        
        return True
    
    def flush_batch(self) -> bool:
        """Flush current batch to ChromaDB"""
        if not self.current_batch['documents']:
            logger.debug("No documents in batch to flush")
            return True
        
        try:
            logger.info(f"Flushing batch of {len(self.current_batch['documents'])} documents")
            
            # Final validation of batch
            valid_indices = []
            for i, (doc, meta) in enumerate(zip(self.current_batch['documents'], self.current_batch['metadatas'])):
                if self.validate_chunk(doc, meta):
                    valid_indices.append(i)
                else:
                    logger.warning(f"Removing invalid chunk from batch at index {i}")
            
            if not valid_indices:
                logger.warning("No valid chunks in batch")
                self.current_batch = {'documents': [], 'metadatas': [], 'ids': []}
                return True
            
            # Filter batch to only valid chunks
            filtered_docs = [self.current_batch['documents'][i] for i in valid_indices]
            filtered_metas = [self.current_batch['metadatas'][i] for i in valid_indices]
            filtered_ids = [self.current_batch['ids'][i] for i in valid_indices]
            
            # Add to collection
            self.collection.add(
                documents=filtered_docs,
                metadatas=filtered_metas,
                ids=filtered_ids
            )
            
            logger.info(f"Successfully added {len(filtered_docs)} documents to collection")
            
            # Clear batch
            self.current_batch = {'documents': [], 'metadatas': [], 'ids': []}
            return True
            
        except Exception as e:
            logger.error(f"Error flushing batch: {e}")
            traceback.print_exc()
            return False
    
    def process_file(self, file_path: str, source_type: str = "unknown") -> bool:
        """Process a single file"""
        logger.info(f"Processing file: {file_path}")
        
        try:
            # Read file content
            content = self.read_file_with_encoding(file_path)
            if not content:
                logger.error(f"Could not read file: {file_path}")
                return False
            
            # Chunk the content
            chunks = self.chunk_text(content)
            if not chunks:
                logger.warning(f"No chunks generated from file: {file_path}")
                return False
            
            logger.info(f"Generated {len(chunks)} chunks from {file_path}")
            
            # Add chunks to batch
            success_count = 0
            for i, chunk in enumerate(chunks):
                metadata = {
                    'source': str(file_path),
                    'source_type': source_type,
                    'chunk_index': i,
                    'total_chunks': len(chunks),
                    'file_name': Path(file_path).name
                }
                
                if self.add_to_batch(chunk, metadata):
                    success_count += 1
                else:
                    logger.warning(f"Failed to add chunk {i} from {file_path}")
            
            logger.info(f"Successfully processed {success_count}/{len(chunks)} chunks from {file_path}")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
            traceback.print_exc()
            return False
    
    def process_directory(self, directory_path: str, source_type: str = "unknown") -> Tuple[int, int]:
        """Process all files in a directory"""
        directory_path = Path(directory_path)
        
        if not directory_path.exists():
            logger.error(f"Directory does not exist: {directory_path}")
            return 0, 0
        
        logger.info(f"Processing directory: {directory_path}")
        
        # Find all text files
        text_extensions = {'.txt', '.md', '.py', '.js', '.html', '.css', '.json', '.xml', '.csv'}
        files = []
        
        for ext in text_extensions:
            files.extend(directory_path.glob(f"**/*{ext}"))
        
        if not files:
            logger.warning(f"No text files found in {directory_path}")
            return 0, 0
        
        logger.info(f"Found {len(files)} files to process")
        
        # Process each file
        success_count = 0
        for file_path in files:
            if self.process_file(str(file_path), source_type):
                success_count += 1
        
        return success_count, len(files)
    
    def finalize(self) -> bool:
        """Finalize ingestion by flushing remaining batches"""
        logger.info("Finalizing ingestion...")
        
        # Flush any remaining batch
        if not self.flush_batch():
            logger.error("Failed to flush final batch")
            return False
        
        # Get collection stats
        try:
            count = self.collection.count()
            logger.info(f"Ingestion complete. Collection contains {count} documents.")
            return True
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return False

def main():
    """Main ingestion process"""
    print("🚀 Starting Document Ingestion")
    print("=" * 50)
    
    # Initialize ingester
    ingester = DocumentIngester()
    
    if not ingester.initialize_chroma():
        logger.error("Failed to initialize ChromaDB")
        return False
    
    # Process internal documents
    if os.path.exists("internal_documents"):
        logger.info("Processing internal documents...")
        success, total = ingester.process_directory("internal_documents", "internal")
        logger.info(f"Internal documents: {success}/{total} files processed successfully")
    else:
        logger.warning("internal_documents directory not found")
    
    # Process output directory
    if os.path.exists("output"):
        logger.info("Processing output directory...")
        success, total = ingester.process_directory("output", "crawled")
        logger.info(f"Output directory: {success}/{total} files processed successfully")
    else:
        logger.warning("output directory not found")
    
    # Finalize
    if ingester.finalize():
        print("\n✅ Ingestion completed successfully!")
        return True
    else:
        print("\n❌ Ingestion failed during finalization")
        return False

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\n🎉 Document ingestion completed successfully!")
            print("You can now test your RAG system.")
        else:
            print("\n💥 Document ingestion failed. Check logs for details.")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n🚫 Ingestion interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        traceback.print_exc()
        sys.exit(1)
