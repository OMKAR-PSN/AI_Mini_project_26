"""One shared, optional Qwen loader. No inference fallback or fabricated answers."""
import time

class ModelUnavailable(RuntimeError): pass

PROMPT = 'Answer the satellite image question with only a short answer, without explanation.\nQuestion: {question}'

def require_gpu(torch, minimum_bytes=10*1024**3):
    if not torch.cuda.is_available(): raise ModelUnavailable('CUDA GPU unavailable; E1/E2 inference not run')
    free, total = torch.cuda.mem_get_info()
    if free < minimum_bytes:
        raise ModelUnavailable(f'Only {free/1024**3:.1f} GiB free; require 10 GiB for this unquantized configuration')
    return dict(gpu=torch.cuda.get_device_name(0), free_bytes=free, total_bytes=total)

class QwenRunner:
    def __init__(self, config):
        try:
            import torch
            self.hardware = require_gpu(torch)
            from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration
            torch.manual_seed(config['seed'])
            torch.backends.cudnn.benchmark = False
            self.processor = AutoProcessor.from_pretrained(config['id'], revision=config['revision'],
                use_fast=False, min_pixels=config['min_pixels'], max_pixels=config['max_pixels'], token=False)
            self.model = Qwen2_5_VLForConditionalGeneration.from_pretrained(config['id'],
                revision=config['revision'], torch_dtype=torch.float16, device_map={'':'cuda:0'},
                attn_implementation='sdpa', token=False).eval()
            self.config, self.torch = config, torch
        except ModelUnavailable: raise
        except Exception as exc: raise ModelUnavailable(f'Model loading failed: {type(exc).__name__}: {exc}') from exc

    def predict(self, image, question):
        torch = self.torch
        messages = [{'role':'user','content':[{'type':'image'},
            {'type':'text','text':PROMPT.format(question=question)}]}]
        text = self.processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        start = time.perf_counter()
        inputs = self.processor(text=[text], images=[image], return_tensors='pt').to('cuda:0')
        torch.cuda.synchronize(); torch.cuda.reset_peak_memory_stats()
        with torch.inference_mode():
            output = self.model.generate(**inputs, do_sample=False, num_beams=1,
                max_new_tokens=self.config['max_new_tokens'], use_cache=True)
        torch.cuda.synchronize()
        raw = self.processor.batch_decode(output[:,inputs.input_ids.shape[1]:],
            skip_special_tokens=True, clean_up_tokenization_spaces=False)[0]
        return dict(prediction_raw=raw, inference_latency_ms=1000*(time.perf_counter()-start),
                    image_grid_thw=inputs.image_grid_thw.tolist(),
                    peak_allocated_bytes=torch.cuda.max_memory_allocated(),
                    peak_reserved_bytes=torch.cuda.max_memory_reserved())
