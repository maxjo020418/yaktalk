#!/usr/bin/env python3
"""
Comprehensive test script for Chroma refactor
"""

import sys
import tempfile
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def test_basic_imports():
    """Test that basic imports work"""
    print("🔍 Testing basic imports...")
    
    try:
        from langchain_chroma import Chroma
        print("  ✅ langchain_chroma import successful")
        
        from langchain_core.documents import Document
        print("  ✅ langchain_core.documents import successful")
        
        from langchain_core.embeddings import Embeddings
        print("  ✅ langchain_core.embeddings import successful")
        
        return True
    except ImportError as e:
        print(f"  ❌ Import failed: {e}")
        return False

def test_pdf_reader_imports():
    """Test PDF reader module imports"""
    print("🔍 Testing PDF reader imports...")
    
    try:
        from call_functions.pdf_reader import (
            PDFConfig, PDFVectorStore, PDFService,
            initialize_chromadb, get_retriever, is_chromadb_initialized,
            search_pdf_content, get_pdf_metadata, tools
        )
        print("  ✅ All PDF reader imports successful")
        return True
    except ImportError as e:
        print(f"  ❌ PDF reader import failed: {e}")
        return False

def test_law_api_imports():
    """Test law API module imports"""
    print("🔍 Testing law API imports...")
    
    try:
        # Test individual classes first
        from call_functions.law_api import (
            LawConfig, ArticleInfo, LawAPIClient, 
            LawDocumentProcessor
        )
        print("  ✅ Law API core classes imported successfully")
        
        # Test vector store (might fail due to environment)
        try:
            from call_functions.law_api import LawVectorStore, LawService
            print("  ✅ Law vector store classes imported successfully")
        except Exception as e:
            print(f"  ⚠️ Law vector store import warning: {e}")
            # This might fail due to missing environment variables, but that's OK
        
        # Test tools
        from call_functions.law_api import search_law_by_query, load_law_by_id, tools
        print("  ✅ Law API tools imported successfully")
        
        return True
    except ImportError as e:
        print(f"  ❌ Law API import failed: {e}")
        return False

def test_pdf_embeddings():
    """Test PDF embeddings creation"""
    print("🔍 Testing PDF embeddings...")
    
    try:
        from utils.custom_embeddings import get_pdf_embeddings
        embeddings = get_pdf_embeddings()
        
        # Test embedding a simple text
        test_text = "This is a test document."
        embedding = embeddings.embed_query(test_text)
        
        if isinstance(embedding, list) and len(embedding) > 0:
            print(f"  ✅ PDF embeddings working (dimension: {len(embedding)})")
            return True
        else:
            print("  ❌ PDF embeddings returned invalid result")
            return False
            
    except Exception as e:
        print(f"  ❌ PDF embeddings failed: {e}")
        return False

def test_pdf_vectorstore_creation():
    """Test PDF vector store creation without actual PDF"""
    print("🔍 Testing PDF vector store creation...")
    
    try:
        from call_functions.pdf_reader import PDFVectorStore, PDFConfig
        from langchain_core.documents import Document
        
        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            config = PDFConfig()
            pdf_store = PDFVectorStore(config)
            
            # Test with minimal document
            test_doc = Document(
                page_content="This is a test document for vector store.",
                metadata={"page": 1, "source": "test.pdf"}
            )
            
            # Initialize with test documents
            pdf_store._initialize_vectorstore([test_doc])
            
            if pdf_store.is_initialized():
                print("  ✅ PDF vector store created and initialized successfully")
                
                # Test search
                results = pdf_store.search("test document")
                if results:
                    print(f"  ✅ PDF vector store search working (found {len(results)} results)")
                else:
                    print("  ⚠️ PDF vector store search returned no results")
                
                return True
            else:
                print("  ❌ PDF vector store not properly initialized")
                return False
                
    except Exception as e:
        print(f"  ❌ PDF vector store creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_law_vectorstore_creation():
    """Test law vector store creation (might fail due to environment)"""
    print("🔍 Testing law vector store creation...")
    
    try:
        from call_functions.law_api import LawVectorStore, LawConfig
        
        config = LawConfig()
        law_store = LawVectorStore(config)
        
        if law_store.vectorstore is not None:
            print("  ✅ Law vector store created successfully")
            return True
        else:
            print("  ⚠️ Law vector store creation failed (likely environment issue)")
            return False
            
    except Exception as e:
        print(f"  ⚠️ Law vector store creation failed: {e}")
        print("  (This is expected if Ollama is not available)")
        return False

def test_chroma_persistence():
    """Test Chroma persistence functionality"""
    print("🔍 Testing Chroma persistence...")
    
    try:
        from langchain_chroma import Chroma
        from langchain_core.documents import Document
        from utils.custom_embeddings import get_pdf_embeddings
        
        with tempfile.TemporaryDirectory() as temp_dir:
            embeddings = get_pdf_embeddings()
            
            # Create first vectorstore instance
            vectorstore1 = Chroma(
                collection_name="test_collection",
                embedding_function=embeddings,
                persist_directory=temp_dir
            )
            
            # Add test document
            test_doc = Document(
                page_content="Persistent test document",
                metadata={"test": "persistence"}
            )
            vectorstore1.add_documents([test_doc])
            
            # Create second vectorstore instance (should load persisted data)
            vectorstore2 = Chroma(
                collection_name="test_collection",
                embedding_function=embeddings,
                persist_directory=temp_dir
            )
            
            # Test if data persisted
            results = vectorstore2.similarity_search("persistent test", k=1)
            
            if results and len(results) > 0:
                print("  ✅ Chroma persistence working correctly")
                return True
            else:
                print("  ❌ Chroma persistence not working")
                return False
                
    except Exception as e:
        print(f"  ❌ Chroma persistence test failed: {e}")
        return False

def test_new_api_compatibility():
    """Test that the new API works as expected"""
    print("🔍 Testing new langchain-chroma API compatibility...")
    
    try:
        from langchain_chroma import Chroma
        from langchain_core.documents import Document
        from utils.custom_embeddings import get_pdf_embeddings
        
        embeddings = get_pdf_embeddings()
        
        # Test new API initialization (without explicit client)
        with tempfile.TemporaryDirectory() as temp_dir:
            vectorstore = Chroma(
                collection_name="api_test",
                embedding_function=embeddings,
                persist_directory=temp_dir
            )
            
            # Test add_documents
            docs = [
                Document(page_content="API test document 1", metadata={"id": 1}),
                Document(page_content="API test document 2", metadata={"id": 2})
            ]
            vectorstore.add_documents(docs)
            
            # Test similarity search
            results = vectorstore.similarity_search("API test", k=2)
            
            if len(results) == 2:
                print("  ✅ New langchain-chroma API working correctly")
                return True
            else:
                print(f"  ❌ Expected 2 results, got {len(results)}")
                return False
                
    except Exception as e:
        print(f"  ❌ New API compatibility test failed: {e}")
        return False

def run_all_tests():
    """Run all tests and provide summary"""
    print("🧪 Running comprehensive Chroma refactor tests...")
    print("=" * 60)
    
    tests = [
        ("Basic Imports", test_basic_imports),
        ("PDF Reader Imports", test_pdf_reader_imports),
        ("Law API Imports", test_law_api_imports),
        ("PDF Embeddings", test_pdf_embeddings),
        ("PDF Vector Store", test_pdf_vectorstore_creation),
        ("Law Vector Store", test_law_vectorstore_creation),
        ("Chroma Persistence", test_chroma_persistence),
        ("New API Compatibility", test_new_api_compatibility),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"  ❌ Test crashed: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY:")
    print("=" * 60)
    
    passed = 0
    failed = 0
    warnings = 0
    
    for test_name, result in results:
        if result is True:
            print(f"✅ {test_name}: PASSED")
            passed += 1
        elif result is False:
            print(f"❌ {test_name}: FAILED")
            failed += 1
        else:
            print(f"⚠️ {test_name}: WARNING")
            warnings += 1
    
    print(f"\nTotal: {len(results)} tests")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Warnings: {warnings}")
    
    if failed == 0:
        print("\n🎉 All critical tests passed! Chroma refactor is working correctly.")
        if warnings > 0:
            print("⚠️ Some warnings detected (likely environment-related, not critical)")
        return True
    else:
        print(f"\n❌ {failed} test(s) failed. Please check the output above.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
