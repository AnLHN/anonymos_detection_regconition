import onnxruntime as ort


CUDA_PROVIDER_OPTIONS = {
    "cudnn_conv_algo_search": "DEFAULT",
    "cudnn_conv_use_max_workspace": "0",
    "prefer_nhwc": "0",
    "use_tf32": "1",
}


def insightface_providers(device: str) -> tuple[list[str], list[dict[str, str]], int]:
    available = set(ort.get_available_providers())
    requested_cuda = device.lower() == "cuda"
    if requested_cuda and "CUDAExecutionProvider" in available:
        print(f"InsightFace ONNX providers: CUDAExecutionProvider, CPUExecutionProvider options={CUDA_PROVIDER_OPTIONS}")
        return ["CUDAExecutionProvider", "CPUExecutionProvider"], [CUDA_PROVIDER_OPTIONS, {}], 0
    if requested_cuda:
        print(f"InsightFace CUDA requested but unavailable. Available ONNX providers: {sorted(available)}")
    else:
        print(f"InsightFace ONNX providers: CPUExecutionProvider. Available providers: {sorted(available)}")
    return ["CPUExecutionProvider"], [{}], -1
