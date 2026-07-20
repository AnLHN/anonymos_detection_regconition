from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import tensorrt as trt
from cuda.bindings import runtime as cudart


TRT_TO_NUMPY = {
    trt.DataType.FLOAT: np.float32,
    trt.DataType.HALF: np.float16,
    trt.DataType.INT32: np.int32,
    trt.DataType.INT64: np.int64,
    trt.DataType.BOOL: np.bool_,
    trt.DataType.UINT8: np.uint8,
}


@dataclass(frozen=True)
class TensorInfo:
    name: str
    shape: list[int | str]


class TensorRTInferenceSession:
    def __init__(self, engine_path: str | Path) -> None:
        self.engine_path = Path(engine_path)
        logger = trt.Logger(trt.Logger.WARNING)
        runtime = trt.Runtime(logger)
        engine = runtime.deserialize_cuda_engine(self.engine_path.read_bytes())
        if engine is None:
            raise RuntimeError(f"Could not deserialize TensorRT engine: {self.engine_path}")

        self.runtime = runtime
        self.engine = engine
        self.context = engine.create_execution_context()
        self.stream = self._check(cudart.cudaStreamCreate())[1]
        self.input_names: list[str] = []
        self.output_names: list[str] = []
        self.tensor_shapes: dict[str, tuple[int, ...]] = {}
        self.tensor_dtypes: dict[str, Any] = {}
        self.device_buffers: dict[str, int] = {}
        self.buffer_sizes: dict[str, int] = {}

        for index in range(engine.num_io_tensors):
            name = engine.get_tensor_name(index)
            shape = tuple(int(dim) for dim in engine.get_tensor_shape(name))
            dtype = TRT_TO_NUMPY.get(engine.get_tensor_dtype(name))
            if dtype is None:
                raise RuntimeError(f"Unsupported TensorRT dtype for {name}: {engine.get_tensor_dtype(name)}")
            self.tensor_shapes[name] = shape
            self.tensor_dtypes[name] = dtype
            nbytes = int(np.prod(shape)) * np.dtype(dtype).itemsize
            self.device_buffers[name] = self._check(cudart.cudaMalloc(nbytes))[1]
            self.buffer_sizes[name] = nbytes
            self.context.set_tensor_address(name, self.device_buffers[name])
            if engine.get_tensor_mode(name) == trt.TensorIOMode.INPUT:
                self.input_names.append(name)
            else:
                self.output_names.append(name)

    def __del__(self) -> None:
        for ptr in getattr(self, "device_buffers", {}).values():
            if ptr:
                cudart.cudaFree(ptr)
        stream = getattr(self, "stream", None)
        if stream:
            cudart.cudaStreamDestroy(stream)

    def get_inputs(self) -> list[TensorInfo]:
        return [TensorInfo(name=name, shape=list(self.tensor_shapes[name])) for name in self.input_names]

    def get_outputs(self) -> list[TensorInfo]:
        return [TensorInfo(name=name, shape=list(self.tensor_shapes[name])) for name in self.output_names]

    def run(self, output_names: list[str] | None, input_feed: dict[str, np.ndarray]) -> list[np.ndarray]:
        names = output_names or self.output_names
        for name in self.input_names:
            array = np.ascontiguousarray(input_feed[name], dtype=self.tensor_dtypes[name])
            expected = self.tensor_shapes[name]
            if tuple(array.shape) != expected:
                raise ValueError(f"TensorRT input {name} expected shape {expected}, got {tuple(array.shape)}")
            self._check(
                cudart.cudaMemcpyAsync(
                    self.device_buffers[name],
                    array.ctypes.data,
                    array.nbytes,
                    cudart.cudaMemcpyKind.cudaMemcpyHostToDevice,
                    self.stream,
                )
            )

        if not self.context.execute_async_v3(self.stream):
            raise RuntimeError(f"TensorRT execution failed for {self.engine_path}")

        outputs: list[np.ndarray] = []
        for name in names:
            output = np.empty(self.tensor_shapes[name], dtype=self.tensor_dtypes[name])
            self._check(
                cudart.cudaMemcpyAsync(
                    output.ctypes.data,
                    self.device_buffers[name],
                    output.nbytes,
                    cudart.cudaMemcpyKind.cudaMemcpyDeviceToHost,
                    self.stream,
                )
            )
            outputs.append(output)
        self._check(cudart.cudaStreamSynchronize(self.stream))
        return outputs

    @staticmethod
    def _check(result):
        error = result[0] if isinstance(result, tuple) else result
        if error != cudart.cudaError_t.cudaSuccess:
            raise RuntimeError(f"CUDA runtime error: {error}")
        return result
