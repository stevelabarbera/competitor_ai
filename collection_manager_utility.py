from collection_manager import CollectionManager
from pathlib import Path
import os
import logging
import chromadb

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Paths
ROOT_DIR = Path(__file__).resolve().parents[0]
INTERNAL_DATA_DIR = ROOT_DIR 
TARGET_DEFINITION='get_competitor_collection'


def get_competitor_collection(client, create_if_not_exists=True):
    manager = CollectionManager()
    return manager.get_collection("competitor_docs")



def collection_manager_replacement_locations(project_root):
    logger.info(f"Attempting to enumerate the directory {project_root} ")
    for subdir, _, files in os.walk(project_root):
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(subdir, file)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        text = f.read()
                        logger.info(f"Looking in file for TARGET_DEFINITION: {TARGET_DEFINITION}")
                    if 'get_competitor_collection' in text:
                        print(f"✔️  Replace in {path}")
                except:
                    continue

if __name__ == "__main__":

   #collection_manager_replacement_locations(INTERNAL_DATA_DIR)
    mgr = CollectionManager()
    this_client = mgr.get_client()
    names = this_client.list_collections()
    for name in names:
        logger.info("Showing collection with the name: {name}")
        # Get documents without any filters first
        results = name.get()
        '''
        results = name.get(
            limit=10,
            include=['documents', 'metadatas']
        )
        '''
        logger.info(f"collection name: {results}")
    '''
    col = mgr.get_collection("docs_censys"
    results = col.query(query_texts=["attack surface management"], n_results=5)
    print("IDs:", results.get("ids", [[]])[0])
    print("Docs:", results.get("documents", [[]])[0])
    print("Metas:", results.get("metadatas", [[]])[0])
    '''
