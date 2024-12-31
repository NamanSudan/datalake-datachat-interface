import os
from setuptools import setup, find_packages

# Read requirements.txt
with open("requirements.txt") as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith("--")]

# Get version from environment or default to development version
version = os.getenv("VLLM_VERSION", "0.6.1")

setup(
    name="vllm",
    version=version,
    description="A high-throughput and memory-efficient inference engine for LLMs",
    long_description=open("README.md").read() if os.path.exists("README.md") else "",
    long_description_content_type="text/markdown",
    author="vLLM Team",
    author_email="team@vllm.ai",
    url="https://github.com/vllm-project/vllm",
    license="Apache-2.0",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=requirements,
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
) 