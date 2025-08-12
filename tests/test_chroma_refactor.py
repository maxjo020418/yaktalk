#!/usr/bin/env python3
"""
Test script to verify the Chroma refactor works correctly
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

def test_imports():
    """Test that all imports work correctly"""
    try:
        # Test PDF reader imports
        from call_functions.pdf_reader import PDFService, PDFVectorStore
        print("✅ PDF reader imports successful")
        
        # Test law API imports  
        from call_functions.law_api import LawService, LawVectorStore
        print("✅ Law API imports successful")
        
        # Test direct langchain_chroma import
        from langchain_chroma import Chroma
        print("✅ langchain_chroma import successful")
        
        return True
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        return False

def test_vectorstore_initialization():
    """Test that vector stores can be initialized"""
    try:
        from call_functions.pdf_reader import PDFVectorStore, PDFConfig
        
        # Test PDF vector store initialization
        config = PDFConfig()
        pdf_store = PDFVectorStore(config)
        print("✅ PDF vector store initialization successful")
        
        from call_functions.law_api import LawVectorStore, LawConfig
        
        # Test law vector store initialization  
        law_config = LawConfig()
        law_store = LawVectorStore(law_config)
        print("✅ Law vector store initialization successful")
        
        return True
    except Exception as e:
        print(f"❌ Vector store initialization test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("🧪 Testing Chroma refactor...")
    print()
    
    # Test imports
    print("1. Testing imports...")
    import_success = test_imports()
    print()
    
    # Test initialization
    print("2. Testing vector store initialization...")
    init_success = test_vectorstore_initialization()
    print()
    
    # Summary
    if import_success and init_success:
        print("🎉 All tests passed! Chroma refactor is working correctly.")
        return True
    else:
        print("❌ Some tests failed. Please check the output above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
