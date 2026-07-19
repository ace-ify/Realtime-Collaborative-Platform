import sys
import os
# Project root directory ko Python path me add karein
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pycrdt as Y
from app.diff_utils import apply_diff_to_ytext

def test_smart_diff():
    doc = Y.Doc()
    text = doc.get("text", type=Y.Text)
    
    # 1. Document ko ek initial state de dete hain
    initial_content = "The quick brown fox jumps over the lazy dog."
    with doc.transaction():
        text += initial_content
        
    print(f"Initial Doc content: '{str(text)}'")
    
    # 2. AI ka revised proposal (kuch words change hue hain)
    ai_suggestion = "The fast red fox jumps over the active dog."
    
    # 3. Apply smart diff changes
    apply_diff_to_ytext(text, initial_content, ai_suggestion, doc)
    
    # 4. Verify results
    final_content = str(text)
    print(f"Final Doc content  : '{final_content}'")
    
    assert final_content == ai_suggestion
    print("✅ Success: Smart diff applied and verified successfully!")

if __name__ == "__main__":
    test_smart_diff()
