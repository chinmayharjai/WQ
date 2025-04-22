import os
import glob
from bs4 import BeautifulSoup
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import GoogleGenerativeAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain.document_loaders import DirectoryLoader
from langchain.document_loaders import TextLoader
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure Google API key
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

def extract_text_from_html(html_content):
    """Extract clean text from HTML content"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.decompose()
    
    # Get text
    text = soup.get_text()
    
    # Break into lines and remove leading and trailing space
    lines = (line.strip() for line in text.splitlines())
    # Break multi-headlines into a line each
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    # Drop blank lines
    text = '\n'.join(chunk for chunk in chunks if chunk)
    
    return text

def load_and_process_html_files(directory):
    """Load and process all HTML files from the directory"""
    documents = []
    
    # Get all HTML files recursively
    html_files = glob.glob(os.path.join(directory, "**/*.html"), recursive=True)
    
    for html_file in html_files:
        try:
            with open(html_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
                text = extract_text_from_html(html_content)
                
                # Create a document with metadata
                doc = {
                    "page_content": text,
                    "metadata": {
                        "source": html_file,
                        "title": os.path.basename(html_file)
                    }
                }
                documents.append(doc)
        except Exception as e:
            print(f"Error processing {html_file}: {str(e)}")
    
    return documents

def setup_rag_chain():
    """Set up the RAG chain with Gemini"""
    # Initialize the LLM
    llm = ChatGoogleGenerativeAI(
        model="gemini-pro",
        temperature=0.3,
        google_api_key=GOOGLE_API_KEY
    )
    
    # Initialize embeddings
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/embedding-001",
        google_api_key=GOOGLE_API_KEY
    )
    
    # Load and process documents
    print("Loading and processing HTML files...")
    documents = load_and_process_html_files("scraped_support_content")
    
    # Split documents into chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )
    
    texts = [doc["page_content"] for doc in documents]
    metadatas = [doc["metadata"] for doc in documents]
    
    # Create vector store
    print("Creating vector store...")
    vectorstore = FAISS.from_texts(
        texts=texts,
        embedding=embeddings,
        metadatas=metadatas
    )
    
    # Create retriever
    retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 4}
    )
    
    # Create QA chain
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=True
    )
    
    return qa_chain

def main():
    # Check if Google API key is set
    if not GOOGLE_API_KEY:
        print("Error: GOOGLE_API_KEY environment variable is not set")
        return
    
    # Set up RAG chain
    qa_chain = setup_rag_chain()
    
    print("\nRAG system is ready! Ask questions about the WorldQuant Brain support content.")
    print("Type 'exit' to quit.")
    
    while True:
        query = input("\nYour question: ")
        if query.lower() == 'exit':
            break
        
        try:
            result = qa_chain({"query": query})
            print("\nAnswer:", result["result"])
            print("\nSources:")
            for doc in result["source_documents"]:
                print(f"- {doc.metadata['source']}")
        except Exception as e:
            print(f"Error: {str(e)}")

if __name__ == "__main__":
    main() 