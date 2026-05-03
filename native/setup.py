from setuptools import Extension, setup
from pybind11.setup_helpers import build_ext
import pybind11

ext_modules = [
    Extension(
        "memoryfeed_native",
        ["memoryfeed_native.cpp"],
        include_dirs=[pybind11.get_include()],
        language="c++",
        extra_compile_args=["/O2", "/std:c++17"] if __import__("sys").platform.startswith("win") else ["-O3", "-std=c++17"],
    )
]

setup(
    name="memoryfeed-native",
    version="0.1.0",
    ext_modules=ext_modules,
    cmdclass={"build_ext": build_ext},
)
