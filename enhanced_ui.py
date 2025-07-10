import gradio as gr
from search_engine import ask_enhanced, debug_collection_content
from ingest_internal_doc import ingest_documents_from_directories
import chromadb
from embedding_config import get_competitor_collection

# === Enhanced Ask/Answer with Advanced Options ===
def ask_and_debug_enhanced(question, mode, source_filter, use_reranking, show_debug):
    # Clean source filter
    source_filter = source_filter.strip() if source_filter and source_filter.strip() else None
    
    # Get the answer
    answer = ask_enhanced(
        question, 
        mode=mode, 
        source_filter=source_filter, 
        use_reranking=use_reranking
    )
    
    # Prepare debug info
    debug_info = f"✅ Mode: {mode}\n"
    if source_filter:
        debug_info += f"🔍 Source filter: {source_filter}\n"
    debug_info += f"🧠 Reranking: {'Enabled' if use_reranking else 'Disabled'}\n"
    
    # Add collection debug info if requested
    collection_debug = ""
    if show_debug:
        try:
            client = chromadb.PersistentClient(path="./chroma_db")
            collection = get_competitor_collection(client)
            
            # Get some basic stats
            count = collection.count()
            debug_info += f"📊 Total chunks in collection: {count}\n"
            
            # Sample search to show what's being retrieved
            results = collection.query(query_texts=[question], n_results=3)
            docs = results.get("documents", [[]])[0]
            metadatas = results.get("metadatas", [[]])[0]
            
            collection_debug = "\n🔍 SAMPLE RETRIEVED CHUNKS:\n"
            for i, (doc, meta) in enumerate(zip(docs[:2], metadatas[:2])):
                collection_debug += f"\n--- Chunk {i+1} ---\n"
                collection_debug += f"Source: {meta.get('source', 'Unknown')}\n"
                collection_debug += f"Preview: {doc[:150]}...\n"
                collection_debug += f"Words: {len(doc.split())}\n"
                
        except Exception as e:
            collection_debug = f"❌ Debug error: {e}"
    
    return answer, debug_info + collection_debug

# === Collection Analysis Function ===
def analyze_collection():
    try:
        client = chromadb.PersistentClient(path="./chroma_db")
        collection = get_competitor_collection(client)
        
        count = collection.count()
        
        # Get a sample of documents to analyze sources
        sample = collection.get(limit=min(100, count))
        sources = {}
        
        for meta in sample.get("metadatas", []):
            source = meta.get("source", "Unknown")
            sources[source] = sources.get(source, 0) + 1
        
        analysis = f"📊 COLLECTION ANALYSIS\n"
        analysis += f"Total chunks: {count}\n\n"
        analysis += "📁 Sources breakdown:\n"
        
        for source, chunk_count in sorted(sources.items(), key=lambda x: x[1], reverse=True):
            analysis += f"  • {source}: {chunk_count} chunks\n"
        
        return analysis
        
    except Exception as e:
        return f"❌ Analysis failed: {e}"

# === Ingestion Trigger Function ===
def trigger_ingestion(chunk_size, overlap, include_pdf, exclude_ext, directories):
    try:
        # Parse directories
        dir_list = [d.strip() for d in directories.split(",") if d.strip()]
        if not dir_list:
            dir_list = ["internal_data", "output"]
        
        status = ingest_documents_from_directories(
            dir_list,
            chunk_size=chunk_size,
            overlap=overlap,
            include_pdf=include_pdf,
            exclude_ext=exclude_ext
        )
        return status or "✅ Ingestion completed successfully."
    except Exception as e:
        return f"❌ Ingestion failed: {str(e)}"

# === Tab 1: Enhanced Ask Questions ===
with gr.Blocks() as tab1:
    gr.Markdown("# 📊 Enhanced Competitive Intelligence Chat")
    gr.Markdown("Ask questions about your competitors with advanced search options.")
    
    with gr.Row():
        with gr.Column(scale=2):
            question_input = gr.Textbox(
                label="Ask a question about your competitors",
                lines=3,
                placeholder="e.g., What are the pricing models of our main competitors?"
            )
            
            with gr.Row():
                mode_dropdown = gr.Dropdown(
                    ["semantic", "keyword", "hybrid", "full"],
                    label="Search Mode",
                    value="semantic",
                    info="Semantic: AI-powered similarity search | Keyword: Traditional text search | Hybrid: Both combined | Full: Search entire context"
                )
                
                use_reranking = gr.Checkbox(
                    label="Use AI Reranking",
                    value=True,
                    info="Improves result relevance but slower"
                )
            
            with gr.Row():
                source_filter = gr.Textbox(
                    label="Source Filter (optional)",
                    placeholder="e.g., competitor_analysis.pdf",
                    info="Filter results to specific document sources"
                )
                
                show_debug = gr.Checkbox(
                    label="Show Debug Info",
                    value=False,
                    info="Show sample chunks and collection stats"
                )
            
            submit_btn = gr.Button("🔍 Ask Question", variant="primary")
        
        with gr.Column(scale=1):
            gr.Markdown("### 💡 Tips for Better Results")
            gr.Markdown("""
            - **Semantic mode**: Best for conceptual questions
            - **Keyword mode**: Best for specific terms/names
            - **Hybrid mode**: Combines both approaches
            - **Source filter**: Use exact filename to focus search
            - **AI Reranking**: Improves relevance but takes longer
            """)
    
    with gr.Row():
        answer_output = gr.Textbox(
            label="🤖 AI Answer",
            lines=12,
            interactive=False
        )
        
        debug_output = gr.Textbox(
            label="🔧 Debug Information",
            lines=12,
            interactive=False
        )
    
    submit_btn.click(
        fn=ask_and_debug_enhanced,
        inputs=[question_input, mode_dropdown, source_filter, use_reranking, show_debug],
        outputs=[answer_output, debug_output]
    )

# === Tab 2: Collection Analysis ===
with gr.Blocks() as tab2:
    gr.Markdown("# 📈 Collection Analysis")
    gr.Markdown("Analyze your document collection to understand what data is available.")
    
    analyze_btn = gr.Button("🔍 Analyze Collection", variant="primary")
    analysis_output = gr.Textbox(
        label="Collection Analysis Results",
        lines=15,
        interactive=False
    )
    
    analyze_btn.click(
        fn=analyze_collection,
        outputs=analysis_output
    )

# === Tab 3: Document Ingestion ===
with gr.Blocks() as tab3:
    gr.Markdown("# 📥 Document Ingestion")
    gr.Markdown("Ingest documents from your folders into the search database.")
    
    with gr.Row():
        with gr.Column():
            directories_input = gr.Textbox(
                label="Directories to ingest",
                value="internal_data,output",
                info="Comma-separated list of folder names"
            )
            
            chunk_size = gr.Slider(
                minimum=128,
                maximum=1024,
                step=64,
                value=512,
                label="Chunk Size",
                info="Larger chunks = more context, smaller chunks = more precise"
            )
            
            chunk_overlap = gr.Slider(
                minimum=0,
                maximum=256,
                step=32,
                value=64,
                label="Chunk Overlap",
                info="How much chunks should overlap (prevents splitting key info)"
            )
            
        with gr.Column():
            include_pdf = gr.Checkbox(
                label="Include PDFs",
                value=False,
                info="Process PDF files (requires PyMuPDF)"
            )
            
            exclude_ext = gr.Textbox(
                label="Exclude Extensions",
                placeholder="md|docx|xlsx",
                info="Pipe-separated list of file extensions to skip"
            )
            
            ingest_btn = gr.Button("📥 Start Ingestion", variant="primary")
    
    ingestion_output = gr.Textbox(
        label="Ingestion Status",
        lines=10,
        interactive=False
    )
    
    ingest_btn.click(
        fn=trigger_ingestion,
        inputs=[chunk_size, chunk_overlap, include_pdf, exclude_ext, directories_input],
        outputs=ingestion_output
    )

# === Launch Interface with Tabs ===
demo = gr.TabbedInterface(
    [tab1, tab2, tab3],
    ["🔍 Ask Questions", "📈 Analyze Collection", "📥 Ingest Documents"],
    title="🎯 Competitive Intelligence RAG System"
)

if __name__ == "__main__":
    demo.launch(share=False, server_name="0.0.0.0", server_port=7860)
