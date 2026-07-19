from diff_match_patch import diff_match_patch
import pycrdt as Y

def apply_diff_to_ytext(ytext: Y.Text, old_text: str, new_text: str, doc: Y.Doc):
    """
    Takes the collaborative Y.Text object, compares old_text and new_text,
    and applies only the minimum necessary insertions and deletions.
    """
    dmp = diff_match_patch()
    diffs = dmp.diff_main(old_text, new_text)
    # diff_cleanupSemantic cleans up the diff to make it more human-readable
    dmp.diff_cleanupSemantic(diffs)    
    idx = 0  # Tracks the current cursor position in Y.Text
    
    # Hum saare updates ko single transaction me wrap karenge
    with doc.transaction():
        for op, text in diffs:
            if op == 0:
                # 0 means EQUAL: No change, just advance the cursor
                idx += len(text)
            elif op == -1:
                # -1 means DELETE: Delete characters at the current cursor
                del ytext[idx : idx + len(text)]
                # Note: We do NOT increment idx, because deleting shifts the remaining text to the left
            elif op == 1:
                # 1 means INSERT: Insert new text at the current cursor
                ytext.insert(idx, text)
                # Advance cursor by the length of inserted text
                idx += len(text)
