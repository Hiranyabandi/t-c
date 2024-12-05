import os

import streamlit as st
import json
from dotenv import load_dotenv
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings


def setup_environment():
    """Setup environment variables and API key"""
    # Load environment variables
    load_dotenv()

    # Set OpenAI API key
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        os.environ["OPENAI_API_KEY"] = api_key
        return True
    return False


def create_retriever(vector_store, k=3):
    """Create a retriever from the vector store"""
    return vector_store.as_retriever(search_kwargs={"k": k})

def load_metadata(metadata_file):
    """
    Load metadata from a JSON file.

    Args:
        metadata_file (str): Path to the metadata.json file.

    Returns:
        list: A list of metadata dictionaries.
    """
    with open(metadata_file, "r") as f:
        return json.load(f)


def create_documents_with_metadata(metadata_list, data_folder, chunk_size=1000, chunk_overlap=200):
    """
    Create documents with metadata and content chunks.
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap, length_function=len
    )
    documents = []

    for meta in metadata_list:
        file_path = os.path.join(data_folder, meta["filename"])
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as file:
                text = file.read()
                chunks = text_splitter.create_documents([text])
                for chunk in chunks:
                    chunk.metadata = meta  # Attach metadata
                documents.extend(chunks)
        else:
            print(f"Error: File {file_path} does not exist for metadata: {meta}")
            raise FileNotFoundError(f"File {file_path} not found.")
    return documents


def initialize_vectorstore_with_metadata(metadata_file, data_folder, chunk_size=1000, chunk_overlap=200):
    """
    Initialize the FAISS vectorstore with metadata and content chunks.

    Args:
        metadata_file (str): Path to the metadata.json file.
        data_folder (str): Path to the folder containing text files.
        chunk_size (int): Size of each text chunk.
        chunk_overlap (int): Overlap between text chunks.

    Returns:
        FAISS: A FAISS vectorstore object with documents and metadata.
    """
    # Load metadata
    with open(metadata_file, "r") as f:
        metadata_list = json.load(f)

    # Initialize text splitter and embeddings
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap, length_function=len
    )
    embeddings = OpenAIEmbeddings()

    # Create chunks with metadata
    documents = []
    for meta in metadata_list:
        file_path = os.path.join(data_folder, meta["filename"])
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as file:
                text = file.read()
            chunks = text_splitter.create_documents([text])
            for chunk in chunks:
                chunk.metadata = meta  # Attach metadata
            documents.extend(chunks)

    # Create FAISS vectorstore
    return FAISS.from_documents(documents, embeddings)



@st.cache_resource
def initialize_rag(metadata_file="frontend/data/metadata.json", data_folder="frontend/data/", k=2):
    """
    Initialize the RAG system with metadata and context.

    Args:
        metadata_file (str): Path to the metadata file.
        data_folder (str): Path to the folder containing text files.
        k (int): Number of documents to retrieve.

    Returns:
        retriever: A retriever initialized with metadata and documents.
    """
    if not setup_environment():
        raise ValueError("Failed to load API key")

    try:
        vectorstore = initialize_vectorstore_with_metadata(metadata_file, data_folder)
        return vectorstore.as_retriever(search_kwargs={"k": k})
    except Exception as e:
        raise ValueError(f"Failed to initialize RAG system: {e}")



def encode_documents(path, chunk_size=1000, chunk_overlap=200):
    """
    Encodes all text files into a vector store using OpenAI embeddings and includes metadata.

    Args:
        path: The path to the directory of text files.
        chunk_size: The desired size of each text chunk.
        chunk_overlap: The amount of overlap between consecutive chunks.

    Returns:
        A FAISS vector store containing the encoded content and metadata of the files.
    """
    metadata_path = os.path.join(path, "metadata.json")
    with open(metadata_path, "r") as meta_file:
        metadata_list = json.load(meta_file)

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap, length_function=len
    )
    embeddings = OpenAIEmbeddings()

    documents_with_metadata = []

    for meta in metadata_list:
        print(f"Processing file: {meta['filename']} with metadata: {meta}")
        file_path = os.path.join(path, meta["filename"])
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as file:
                text = file.read()

            # Split the text into chunks
            chunks = text_splitter.create_documents([text])

            # Add metadata to each chunk
            for chunk in chunks:
                chunk.metadata = meta  # Attach metadata to each chunk
            documents_with_metadata.extend(chunks)
        else:
            print(f"Error: File {file_path} does not exist for metadata: {meta}")
            raise FileNotFoundError(f"File {file_path} not found.")

    # Ensure metadata is stored in vectorstore
    return FAISS.from_documents(documents_with_metadata, embeddings)



