import importlib.util
import sys


def check_package(name: str) -> None:
    spec = importlib.util.find_spec(name)
    status = "OK" if spec else "MISSING"
    print(f"{name}: {status}")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    print("Python:", sys.version)
    check_package("cv2")
    check_package("numpy")
    check_package("onnxruntime")
    check_package("insightface")


if __name__ == "__main__":
    main()
