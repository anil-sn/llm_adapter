import os

filepath = '/home/asrirang/Coding/llm_adapter/.venv/lib/python3.12/site-packages/vllm/third_party/flashmla/flash_mla_interface.py'
with open(filepath, 'r') as f:
    text = f.read()

target_block = """                kv_b = k_cache_fp32[block_idx, pos_idx]
                # Force 3D layout [active_len, H_k, D_kv] to handle any PyTorch advanced indexing outputs robustly
                kv_b = kv_b.view(active_len, H_k, D_kv)
                k_b = kv_b.transpose(0, 1)
                v_b = kv_b.transpose(0, 1)
                q_b = q_fp32[b].transpose(0, 1)
                
                if H_k == 1 and H > 1:
                    k_b = k_b.expand(H, active_len, D_kv)
                    v_b = v_b.expand(H, active_len, D_kv)
                    
                attn_out = F.scaled_dot_product_attention(
                    q_b, k_b, v_b,
                    scale=softmax_scale
                )
                out[b].copy_(attn_out.transpose(0, 1).to(out.dtype))"""

replacement_block = """                kv_b = k_cache_fp32[block_idx, pos_idx]
                # Force 3D layout [active_len, H_k, D_kv] to handle any PyTorch advanced indexing outputs robustly
                kv_b = kv_b.view(active_len, H_k, D_kv)
                
                # Split Key and Value elements for MLA attention computation:
                # First 512 elements are NoPE (quantized/scaled), last 64 elements are RoPE (unquantized/unscaled)
                kv_b_nope = kv_b[:, 0, :512]  # [active_len, 512]
                kv_b_rope = kv_b[:, 0, 512:]  # [active_len, 64]
                
                # Extract Query parts:
                q_b = q_fp32[b, 0]             # [H, 576]
                q_b_nope = q_b[:, :512]        # [H, 512]
                q_b_rope = q_b[:, 512:]        # [H, 64]
                
                # Key parts transposed:
                k_b_nope = kv_b_nope.transpose(0, 1) # [512, active_len]
                k_b_rope = kv_b_rope.transpose(0, 1) # [64, active_len]
                
                # Expand Keys/Values for multi-head queries (broadcast key heads to match query heads)
                k_b_nope_exp = k_b_nope.unsqueeze(0).expand(H, 512, active_len)
                k_b_rope_exp = k_b_rope.unsqueeze(0).expand(H, 64, active_len)
                v_b_exp = kv_b_nope.unsqueeze(0).transpose(1, 2).expand(H, active_len, 512)
                
                # Compute QK^T:
                # scores_nope = Q_nope @ K_nope^T -> [H, 1, active_len]
                scores_nope = torch.bmm(q_b_nope.unsqueeze(1), k_b_nope_exp)
                # scores_rope = Q_rope @ K_rope^T -> [H, 1, active_len]
                scores_rope = torch.bmm(q_b_rope.unsqueeze(1), k_b_rope_exp)
                
                # Sum parts and apply scale:
                scores = (scores_nope + scores_rope) * softmax_scale
                
                # Softmax over active tokens:
                probs = torch.softmax(scores, dim=-1)
                
                # Compute attention output: probs @ V_b -> [H, 1, 512]
                attn_out = torch.bmm(probs, v_b_exp)
                
                # Transpose back to [1, H, 512] and write to output buffer
                out[b, 0].copy_(attn_out.squeeze(1).to(out.dtype))"""

assert target_block in text, "Target block not found in flash_mla_interface.py"
text = text.replace(target_block, replacement_block)

with open(filepath, 'w') as f:
    f.write(text)
print("Successfully patched flash_mla_interface.py with exact MLA fallback attention math")
