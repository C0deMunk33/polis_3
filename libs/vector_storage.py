import uuid
from datetime import datetime
from typing import Optional, List, TypeVar, Generic, Type, Any, Dict, Union
import requests
from pydantic import BaseModel
from libs.common import embed_for_nomic_storage, embed_for_nomic_retrieval
from sqlmodel import SQLModel, create_engine, Session, select
import chromadb
from chromadb.config import Settings

# Generic type for the model
T = TypeVar('T', bound=BaseModel)

class VectorStorage(Generic[T]):
    """
    A generic storage class that saves data to both SQLite and ChromaDB.
    """
    def __init__(
        self,
        model_class: Type[T],
        sqlite_db_path: str,
        chroma_db_path: str,
        embed_field: str,
        id_field: str = "id",
        collection_name: str = "vector_data",
        ollama_server: str = "http://localhost:11434",
        default_embedding_model: str = "nomic-embed-text"
    ):
        """
        Initialize the storage.
        
        Args:
            model_class: The Pydantic/SQLModel class to use
            sqlite_db_path: Path to SQLite database
            chroma_db_path: Path to ChromaDB storage
            embed_field: Name of the field to generate embeddings for
            id_field: Name of the ID field in the model
            collection_name: Name of the ChromaDB collection
            ollama_server: URL of the Ollama server
            default_embedding_model: Default model to use for embeddings
        """
        self.model_class = model_class
        self.id_field = id_field
        self.embed_field = embed_field
        self.ollama_server = ollama_server.rstrip('/')
        self.default_embedding_model = default_embedding_model
        
        # Initialize SQLite
        self.sqlite_db_path = sqlite_db_path
        self.sqlite_engine = create_engine(f"sqlite:///{self.sqlite_db_path}")
        
        # Create tables if model is SQLModel
        if issubclass(model_class, SQLModel):
            SQLModel.metadata.create_all(self.sqlite_engine)
        
        # Initialize ChromaDB
        self.chroma_db_path = chroma_db_path
        self.chroma_client = chromadb.PersistentClient(
            path=self.chroma_db_path, 
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Get or create the collection
        try:
            self.collection = self.chroma_client.get_collection(name=collection_name)
            print(f"Using existing collection: {collection_name}")
        except:
            self.collection = self.chroma_client.create_collection(name=collection_name)
            print(f"Created new collection: {collection_name}")
    
    def add(
        self, 
        item: Union[T, Dict[str, Any]], 
        metadata_fields: Optional[List[str]] = None,
        item_id: Optional[str] = None,
        embedding_model: Optional[str] = None
    ) -> str:
        """
        Add an item to both SQLite and ChromaDB.
        
        Args:
            item: The item to store (either model instance or dict)
            metadata_fields: List of fields to include in ChromaDB metadata
            item_id: Optional ID (generates UUID if not provided)
            embedding_model: Optional override for embedding model
            
        Returns:
            The ID of the stored item
        """
        # Convert dict to model if needed
        if isinstance(item, dict):
            model_item = self.model_class(**item)
        else:
            model_item = item
        
        # Convert to dict for easier field access
        item_dict = model_item.model_dump() if hasattr(model_item, 'model_dump') else model_item.dict()
        
        # Generate ID if not provided
        if item_id is None:
            if getattr(model_item, self.id_field, None) is None:
                item_id = str(uuid.uuid4())
                setattr(model_item, self.id_field, item_id)
            else:
                item_id = getattr(model_item, self.id_field)
        else:
            setattr(model_item, self.id_field, item_id)
        
        # Ensure the embed field exists
        if self.embed_field not in item_dict:
            raise ValueError(f"Field '{self.embed_field}' not found in model")
        
        text_to_embed = item_dict[self.embed_field]
        
        # 1. Store in SQLite (if model is SQLModel)
        if issubclass(self.model_class, SQLModel):
            with Session(self.sqlite_engine) as session:
                # Check if record exists by ID
                pk_value = getattr(model_item, self.id_field)
                existing = None
                if pk_value:
                    existing = session.get(self.model_class, pk_value)
                    
                if existing:
                    # Update existing record with new values
                    for key, value in item_dict.items():
                        if key != self.id_field:  # Don't update primary key
                            setattr(existing, key, value)
                    # No need to add existing again as it's already tracked
                else:
                    # Add new record
                    session.add(model_item)
                    
                session.commit()
                
                # Refresh the appropriate object
                if existing:
                    session.refresh(existing)
                else:
                    session.refresh(model_item)
        
        # 2. Generate embedding and store in ChromaDB
        embedding = embed_for_nomic_storage(self.ollama_server, text_to_embed)
        
        # Extract metadata if specified
        metadata = {}
        if metadata_fields:
            for field in metadata_fields:
                if field in item_dict:
                    # Handle datetime objects
                    value = item_dict[field]
                    if isinstance(value, datetime):
                        metadata[field] = value.isoformat()
                    else:
                        metadata[field] = value
        
        self.collection.add(
            ids=[item_id],
            embeddings=[embedding],
            documents=[text_to_embed],
            metadatas=[metadata]
        )
        
        #print(f"Item stored with ID: {item_id}")
        return item_id
    
    def query_similar(
        self, 
        query_text: str, 
        n_results: int = 5,
        filter_criteria: Optional[Dict[str, Any]] = None,
        embedding_model: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Query for similar items based on embedding similarity.
        
        Args:
            query_text: The text to find similar items for
            n_results: Number of results to return
            filter_criteria: Optional filter for metadata
            embedding_model: Optional override for embedding model
            
        Returns:
            List of similar items with their metadata
        """
        # Generate embedding for query
        query_embedding = embed_for_nomic_retrieval(self.ollama_server, query_text)
        
        # Query ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=filter_criteria
        )
        
        # Format results
        formatted_results = []
        for i, (doc_id, doc, metadata, distance) in enumerate(zip(
            results['ids'][0],
            results['documents'][0] if 'documents' in results else [""] * len(results['ids'][0]),
            results['metadatas'][0] if 'metadatas' in results else [{}] * len(results['ids'][0]),
            results['distances'][0]
        )):
            # Get full item from SQLite if it's an SQLModel
            db_item = None
            if issubclass(self.model_class, SQLModel):
                with Session(self.sqlite_engine) as session:
                    db_item = session.get(self.model_class, doc_id)
            
            result = {
                self.id_field: doc_id,
                "content": doc,
                "metadata": metadata,
                "similarity": 1.0 - float(distance),  # Convert distance to similarity score
                "db_item": db_item.model_dump() if db_item and hasattr(db_item, 'model_dump') else 
                           db_item.dict() if db_item else None
            }
            
            formatted_results.append(result)
        
        return formatted_results
    
    def get_by_id(self, item_id: str) -> Optional[T]:
        """
        Retrieve an item from SQLite by ID.
        
        Args:
            item_id: The ID of the item to retrieve
            
        Returns:
            The item or None if not found
        """
        if not issubclass(self.model_class, SQLModel):
            raise TypeError("get_by_id is only available for SQLModel-based models")
            
        with Session(self.sqlite_engine) as session:
            item = session.get(self.model_class, item_id)
            return item

    def get_all(self, limit: int = 10) -> List[T]:
        """
        Retrieve all items from SQLite.
        
        Args:
            limit: Maximum number of items to retrieve
            
        Returns:
            List of all items
        """
        with Session(self.sqlite_engine) as session:
            items = session.exec(select(self.model_class).limit(limit)).all()
            return items
    

# Example usage
if __name__ == "__main__":
    # Example model
    class MemoryDBO(SQLModel, table=True):
        id: Optional[str] = None
        content: str
        created_at: datetime = None
        source: Optional[str] = None
        
    # Initialize storage
    storage = VectorStorage(
        model_class=MemoryDBO,
        sqlite_db_path="memories.db",
        chroma_db_path="./chroma_memories",
        embed_field="content",
        ollama_server="http://localhost:11434"
    )
    
    # Add a new memory
    memory = MemoryDBO(
        content="The quick brown fox jumps over the lazy dog. This is a test memory about animals.",
        created_at=datetime.now(),
        source="test"
    )
    
    memory_id = storage.add(
        item=memory,
        metadata_fields=["created_at", "source"]
    )
    
    # Add another memory using a dictionary
    memory_dict = {
        "content": "Machine learning models can process and generate human language.",
        "created_at": datetime.now(),
        "source": "example"
    }
    
    storage.add(
        item=memory_dict,
        metadata_fields=["created_at", "source"]
    )
    
    # Query for similar memories
    query = "Tell me about artificial intelligence"
    similar_memories = storage.query_similar(
        query_text=query,
        n_results=2,
        filter_criteria={"source": "example"}
    )
    
    print(f"\nQuery: '{query}'")
    print("Similar memories:")
    for i, memory in enumerate(similar_memories):
        print(f"{i+1}. ID: {memory['id']}")
        print(f"   Content: {memory['content']}")
        print(f"   Metadata: {memory['metadata']}")
        print(f"   Similarity: {memory['similarity']:.4f}")
        print()
    
    # Retrieve a specific memory by ID
    retrieved_memory = storage.get_by_id(memory_id)
    if retrieved_memory:
        print(f"Retrieved memory {memory_id}:")
        print(f"Content: {retrieved_memory.content}")
        print(f"Created: {retrieved_memory.created_at}")