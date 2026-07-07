import os
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from dotenv import load_dotenv

load_dotenv()

def build_vectorstore():
    """
    One-time script to build FAISS vector store from semiconductor documents.
    Run this once before starting the chatbot.
    """
    print("Loading documents...")
    loader = DirectoryLoader(
        "data/",
        glob="**/*.txt",
        loader_cls=TextLoader
    )
    documents = loader.load()

    if not documents:
        print("No documents found in data/ folder. Adding sample document...")
        # Create a sample document if none exist
        with open("data/semiconductor_supply_chain.txt", "w") as f:
            f.write("""
ASML is the sole supplier of EUV lithography machines required for advanced chip manufacturing.
TSMC manufactures chips for NVIDIA, AMD, and Apple using ASML machines.
Micron produces DRAM and NAND memory chips used in AI servers and data centers.
NVIDIA's H100 GPU requires high bandwidth memory (HBM) from SK Hynix and Samsung.
Any disruption to TSMC production directly impacts Micron, NVIDIA, and AMD supply chains.
Taiwan Strait geopolitical tension represents the single largest systemic risk to global semiconductor supply.
The Strait of Hormuz disruption affects oil prices which increases semiconductor manufacturing costs.
Intel's struggles in advanced node manufacturing have shifted foundry market share to TSMC.
Samsung competes with Micron in DRAM and NAND memory markets.
Export restrictions on advanced semiconductors to China directly impact Micron's revenue.
ASML export restrictions to China affect long-term Chinese semiconductor independence.
""")
        documents = loader.load()

    print(f"Loaded {len(documents)} documents")

    print("Splitting into chunks...")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )
    chunks = splitter.split_documents(documents)
    print(f"Created {len(chunks)} chunks")

    print("Creating embeddings...")
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    print("Building FAISS vector store...")
    vectorstore = FAISS.from_documents(chunks, embeddings)

    print("Saving vector store...")
    vectorstore.save_local("data/faiss_index")
    print("Vector store built and saved to data/faiss_index ✅")

if __name__ == "__main__":
    build_vectorstore()