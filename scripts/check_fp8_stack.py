import importlib
import torch
import triton
import json


def check_torch_fp8():
    fp8_attrs = [x for x in dir(torch) if "float8" in x.lower()]
    has_target = "float8_e8m0fnu" in fp8_attrs

    return {
        "torch_version": torch.__version__,
        "has_float8_e8m0fnu": has_target,
        "float8_dtypes": fp8_attrs,
    }


def check_triton_fp8():
    tl = importlib.import_module("triton.language")
    attrs = [x for x in dir(tl) if "float8" in x or "fp8" in x]

    return {
        "triton_version": triton.__version__,
        "has_float8_e8m0fnu": hasattr(tl, "float8_e8m0fnu"),
        "triton_fp8_symbols": attrs,
    }


def check_vllm_kernel_stack():
    """
    This is the most important test: forces kernel registry init without server start.
    """

    try:
        from vllm import LLM

        # ultra-minimal init to trigger kernel registration only
        llm = LLM(
            model="facebook/opt-125m",
            dtype="float16",
            max_model_len=1,
            gpu_memory_utilization=0.01,
        )

        return {
            "vllm_init": "SUCCESS",
            "note": "Kernel stack initialized without FP8 trigger",
        }

    except Exception as e:
        return {
            "vllm_init": "FAILED",
            "error": str(e),
        }


def main():
    report = {
        "torch": check_torch_fp8(),
        "triton": check_triton_fp8(),
        "vllm": check_vllm_kernel_stack(),
    }

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
